#!/usr/bin/env python3
"""Interactive CLI to query Claude and Gemini side-by-side."""

import asyncio
import time

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ansari_langgraph.agent import AnsariLangGraph
from ansari_gemini.agent import AnsariGemini
from ansari_agent.utils.pricing import calculate_cost, format_cost

app = typer.Typer()
console = Console()


async def query_backend(backend_name: str, agent, query: str, model: str) -> dict:
    """Query a backend and return results with timing and costs."""
    start = time.time()
    try:
        result = await agent.query_with_citations(query)
        latency = time.time() - start

        # Calculate cost
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
        cost = calculate_cost(model, input_tokens, output_tokens)

        return {
            "backend": backend_name,
            "model": model,
            "success": True,
            "response": result["response"],
            "citations": result["citations"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "latency": latency,
            "error": None,
        }
    except Exception as e:
        latency = time.time() - start
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        return {
            "backend": backend_name,
            "model": model,
            "success": False,
            "response": None,
            "citations": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "latency": latency,
            "error": error_detail,
        }


async def compare_query(
    query: str,
    anthropic_model: str = "claude-sonnet-4-20250514",
    gemini_model: str = "gemini-2.5-pro",
    use_gemini: bool = True,
):
    """Run query on both backends concurrently."""

    console.print(f"\n[bold cyan]Query:[/bold cyan] {query}\n")
    console.print(f"[dim]Anthropic Model: {anthropic_model}[/dim]")
    console.print(f"[dim]Gemini Model: {gemini_model}[/dim]\n")

    # Initialize agents
    claude_agent = AnsariLangGraph(model=anthropic_model)
    tasks = [query_backend("Claude", claude_agent, query, anthropic_model)]

    if use_gemini:
        gemini_agent = AnsariGemini(model=gemini_model)
        tasks.append(query_backend("Gemini", gemini_agent, query, gemini_model))

    # Run queries concurrently
    console.print("[yellow]⏳ Querying backends...[/yellow]\n")
    results = await asyncio.gather(*tasks)

    # Display results
    for result in results:
        backend = result["backend"]
        success = result["success"]
        latency = result["latency"]

        if success:
            response = result["response"]
            citations = result["citations"]
            input_tokens = result["input_tokens"]
            output_tokens = result["output_tokens"]
            cost = result["cost"]

            # Create header with timing and stats
            header = (
                f"[bold green]{backend}[/bold green] "
                f"([cyan]{latency:.2f}s[/cyan], "
                f"{len(citations)} citations, "
                f"{input_tokens}→{output_tokens} tokens, "
                f"{format_cost(cost)})"
            )

            # Add citations section to response
            if citations:
                response += "\n\n---\n\n### Citations\n\n"
                for i, citation in enumerate(citations, 1):
                    # Handle both citation formats
                    if "citation" in citation:
                        ref = citation["citation"]
                    else:
                        surah = citation.get("surah", "?")
                        ayah = citation.get("ayah", "?")
                        ref = f"{surah}:{ayah}"

                    arabic = citation.get("arabic", citation.get("arabic_text", ""))
                    english = citation.get("english", citation.get("english_text", ""))

                    response += f"{i}. **Quran {ref}**\n"
                    if arabic:
                        response += f"   - {arabic}\n"
                    if english:
                        response += f"   - {english}\n"
                    response += "\n"

            # Display in panel
            console.print(Panel(
                Markdown(response),
                title=header,
                border_style="green",
            ))
            console.print()
        else:
            error = result["error"]
            console.print(Panel(
                f"[red]Error:[/red] {error}",
                title=f"[bold red]{backend}[/bold red] ([cyan]{latency:.2f}s[/cyan])",
                border_style="red",
            ))
            console.print()

    # Summary table
    table = Table(title="Summary")
    table.add_column("Backend", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Latency", justify="right")
    table.add_column("Input Tokens", justify="right")
    table.add_column("Output Tokens", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Length", justify="right")

    for result in results:
        status = "✓" if result["success"] else "✗"
        latency = f"{result['latency']:.2f}s"
        length = f"{len(result['response'])} chars" if result["success"] else "N/A"

        if result["success"]:
            input_tok = f"{result['input_tokens']:,}"
            output_tok = f"{result['output_tokens']:,}"
            cost_str = format_cost(result["cost"])
        else:
            input_tok = "N/A"
            output_tok = "N/A"
            cost_str = "N/A"

        table.add_row(
            result["backend"],
            status,
            latency,
            input_tok,
            output_tok,
            cost_str,
            length,
        )

    console.print(table)


@app.command()
def query(
    query_text: str = typer.Argument(..., help="Question to ask"),
    model: str = typer.Option(
        "sonnet-4.5",
        "--model",
        "-m",
        help="Anthropic model: sonnet-4.5, opus-4.1",
    ),
    gemini_model: str = typer.Option(
        "pro",
        "--gemini-model",
        "-g",
        help="Gemini model: pro (2.5-pro), flash (2.5-flash)",
    ),
    gemini: bool = typer.Option(True, "--gemini/--no-gemini", help="Include Gemini"),
):
    """Query Claude and Gemini with the same question."""

    # Map friendly names to model IDs
    anthropic_map = {
        "sonnet-4.5": "claude-sonnet-4-20250514",
        "opus-4.1": "claude-opus-4-20250514",
    }

    gemini_map = {
        "pro": "gemini-2.5-pro",
        "flash": "gemini-2.5-flash",
    }

    anthropic_model = anthropic_map.get(model, model)
    gemini_model_id = gemini_map.get(gemini_model, gemini_model)

    asyncio.run(compare_query(query_text, anthropic_model, gemini_model_id, gemini))


@app.command()
def interactive(
    model: str = typer.Option(
        "sonnet-4.5",
        "--model",
        "-m",
        help="Anthropic model: sonnet-4.5, opus-4.1",
    ),
    gemini_model: str = typer.Option(
        "pro",
        "--gemini-model",
        "-g",
        help="Gemini model: pro (2.5-pro), flash (2.5-flash)",
    ),
    gemini: bool = typer.Option(True, "--gemini/--no-gemini", help="Include Gemini"),
):
    """Interactive mode - ask multiple questions."""

    anthropic_map = {
        "sonnet-4.5": "claude-sonnet-4-20250514",
        "opus-4.1": "claude-opus-4-20250514",
    }

    gemini_map = {
        "pro": "gemini-2.5-pro",
        "flash": "gemini-2.5-flash",
    }

    anthropic_model = anthropic_map.get(model, model)
    gemini_model_id = gemini_map.get(gemini_model, gemini_model)

    console.print(Panel(
        "[bold cyan]LLM Comparison Tool[/bold cyan]\n\n"
        f"Anthropic: {model}\n"
        f"Gemini: {gemini_model if gemini else 'Disabled'}\n\n"
        "Type 'quit' or 'exit' to stop",
        border_style="cyan",
    ))

    while True:
        console.print()
        query_text = console.input("[bold yellow]Query:[/bold yellow] ")

        if query_text.lower() in ["quit", "exit", "q"]:
            console.print("[green]Goodbye![/green]")
            break

        if not query_text.strip():
            continue

        asyncio.run(compare_query(query_text, anthropic_model, gemini_model_id, gemini))


if __name__ == "__main__":
    app()
