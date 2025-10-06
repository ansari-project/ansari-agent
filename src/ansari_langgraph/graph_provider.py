"""Graph cache provider for pre-compiled LangGraph instances."""

import logging
from typing import Dict
from langgraph.graph.state import CompiledStateGraph
from ansari_langgraph.graph import create_graph

logger = logging.getLogger(__name__)

# Global cache of compiled graphs
COMPILED_GRAPHS: Dict[str, CompiledStateGraph] = {}


def initialize_graphs(model_ids: list[str]) -> None:
    """Pre-compile graphs for all models at application startup.

    This is a synchronous, blocking operation and should be called
    once during application initialization, not per-request.

    Args:
        model_ids: List of model IDs to initialize graphs for
    """
    logger.info("Initializing LangGraphs for all models...")

    for model_id in model_ids:
        logger.info(f"  - Compiling graph for {model_id}...")
        COMPILED_GRAPHS[model_id] = create_graph(model=model_id)

    logger.info(f"Graph initialization complete. {len(COMPILED_GRAPHS)} graphs cached.")


def get_graph(model_id: str) -> CompiledStateGraph | None:
    """Get a pre-compiled graph for the given model.

    Args:
        model_id: Model identifier

    Returns:
        Compiled graph or None if not found
    """
    return COMPILED_GRAPHS.get(model_id)
