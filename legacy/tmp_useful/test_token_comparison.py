"""Compare token counts WITH and WITHOUT tool calls to verify overhead."""

import asyncio
from playwright.async_api import async_playwright
import re

async def test_queries(page, query):
    """Submit a query and extract token counts."""

    # Clear input and enter new query
    await page.fill('#query-input', query)
    await page.click('#send-btn')

    # Wait for responses
    await page.wait_for_timeout(30000)

    # Extract token counts for each model
    results = {}
    models = ['gemini-2.5-pro', 'gemini-2.5-flash', 'claude-opus-4-20250514', 'claude-sonnet-4-5-20250929']

    for model_id in models:
        metrics = await page.evaluate(f'''
            () => {{
                const panel = document.querySelector('.model-panel[data-model-id="{model_id}"]');
                if (panel) {{
                    const tokens = panel.querySelector('.tokens');
                    return tokens ? tokens.textContent : null;
                }}
                return null;
            }}
        ''')

        if metrics:
            tokens_match = re.search(r'(\d+) in / (\d+) out', metrics)
            tool_match = re.search(r'\((\d+) tool', metrics)

            if tokens_match:
                results[model_id] = {
                    'in': int(tokens_match.group(1)),
                    'out': int(tokens_match.group(2)),
                    'tools': int(tool_match.group(1)) if tool_match else 0,
                    'raw': metrics
                }

    return results

async def main():
    """Test token counts with and without tool calls."""

    async with async_playwright() as p:
        print("🔍 TOKEN COUNT COMPARISON TEST")
        print("=" * 60)

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to the interface
        await page.goto('http://localhost:8000')
        await page.wait_for_timeout(2000)

        # Test 1: Query that triggers tool use
        print("\n📊 TEST 1: Query WITH tool call")
        print("-" * 60)
        query1 = "What does the Quran say about patience?"
        print(f"Query: '{query1}'")
        print(f"Query length: {len(query1)} chars (~{len(query1)//4} base tokens)")

        results1 = await test_queries(page, query1)

        print("\nResults:")
        for model, data in results1.items():
            if data['tools'] > 0:
                base_in = data['in'] - (data['tools'] * 200)
                base_out = data['out'] - (data['tools'] * 500)
                print(f"\n{model}:")
                print(f"  Total tokens: {data['in']} in / {data['out']} out")
                print(f"  Tool calls: {data['tools']}")
                print(f"  Tool overhead: {data['tools'] * 200} in / {data['tools'] * 500} out")
                print(f"  Base tokens (without overhead): {base_in} in / {base_out} out")

        # Reload page for fresh test
        await page.reload()
        await page.wait_for_timeout(2000)

        # Test 2: Query that should NOT trigger tool use
        print("\n\n📊 TEST 2: Query WITHOUT tool call")
        print("-" * 60)
        query2 = "Hello, how are you today?"
        print(f"Query: '{query2}'")
        print(f"Query length: {len(query2)} chars (~{len(query2)//4} base tokens)")

        results2 = await test_queries(page, query2)

        print("\nResults:")
        for model, data in results2.items():
            print(f"\n{model}:")
            print(f"  Total tokens: {data['in']} in / {data['out']} out")
            print(f"  Tool calls: {data['tools']}")
            if data['tools'] == 0:
                print(f"  ✅ No tool overhead added (as expected)")
            else:
                print(f"  ⚠️ Unexpected tool call!")

        # Analysis
        print("\n\n" + "=" * 60)
        print("📝 ANALYSIS:")
        print("-" * 60)

        # Compare input tokens
        if results1 and results2:
            model = 'gemini-2.5-pro'
            if model in results1 and model in results2:
                diff_in = results1[model]['in'] - results2[model]['in']
                diff_out_avg = sum(results1[m]['out'] - results2[m]['out']
                                  for m in results1 if m in results2) // len(results1)

                print(f"Input token difference (with vs without tool): {diff_in} tokens")
                print(f"Average output token difference: ~{diff_out_avg} tokens")
                print(f"\nExpected overhead per tool call:")
                print(f"  - Input: 200 tokens")
                print(f"  - Output: 500 tokens")

                if abs(diff_in - 200) < 10:  # Allow small variance
                    print(f"\n✅ Token overhead is correctly applied!")
                else:
                    print(f"\n⚠️ Token overhead may not be correct")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())