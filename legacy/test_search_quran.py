"""Test SearchQuran tool integration."""

import anyio
from ansari_agent.tools import search_quran
from ansari_agent.utils import config, setup_logger

logger = setup_logger(__name__)


async def test_search_quran_tool():
    """Test SearchQuran tool with real Kalimat API call."""
    print("\n=== Testing SearchQuran Tool ===\n")

    # Validate config
    try:
        config.validate()
        print("✅ Configuration validated")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease create .env file with required API keys:")
        print("  ANTHROPIC_API_KEY=your_key")
        print("  KALIMAT_API_KEY=your_key")
        return

    # Test tool handler
    print(f"\nTool name: {search_quran.name}")
    print(f"Tool description: {search_quran.description[:100]}...")

    # Call tool with test query
    test_query = "patience"
    print(f'\nCalling tool with query: "{test_query}"')

    result = await search_quran.handler({"query": test_query, "num_results": 3})

    print(f"\n✅ Tool executed successfully")
    print(f"Result type: {type(result)}")
    print(f"Content blocks: {len(result.get('content', []))}")

    # Verify metadata preservation (GATE 1 check)
    print("\n=== GATE 1: Citation Metadata Check ===")
    for i, block in enumerate(result.get("content", [])):
        print(f"\nBlock {i}:")
        print(f"  Type: {block.get('type')}")
        print(f"  Has metadata: {'metadata' in block}")

        if "metadata" in block:
            metadata = block["metadata"]
            print(f"  Citation: {metadata.get('citation')}")
            print(f"  Source type: {metadata.get('source_type')}")
            print(f"  Has Arabic: {bool(metadata.get('arabic'))}")
            print(f"  Has English: {bool(metadata.get('english'))}")

            # Show first 100 chars of text
            text = block.get("text", "")
            print(f"  Text preview: {text[:100]}...")

    # Gate 1 decision
    has_metadata = all("metadata" in b for b in result.get("content", []))
    has_citations = all(
        "citation" in b.get("metadata", {}) for b in result.get("content", [])
    )

    print("\n=== GATE 1 DECISION ===")
    if has_metadata and has_citations:
        print("✅ PASS: All content blocks have citation metadata")
        print("✅ Ready to proceed to Phase 3 (Core Agent)")
    else:
        print("❌ FAIL: Citation metadata missing or incomplete")
        print("❌ STOP: SDK incompatible with Ansari requirements")

    return result


if __name__ == "__main__":
    anyio.run(test_search_quran_tool)
