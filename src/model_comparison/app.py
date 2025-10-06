"""FastAPI application for model comparison."""

import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, FileResponse
from .config import config
from .session import session_manager
from .auth import verify_credentials
from .endpoints import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting model comparison application...")

    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except RuntimeError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # Pre-compile graphs for all models (synchronous, blocking operation)
    # This moves the expensive graph creation to startup instead of per-request
    from ansari_langgraph.graph_provider import initialize_graphs

    logger.info("Pre-compiling LangGraph instances...")
    initialize_graphs(list(config.MODELS.keys()))
    logger.info("Graph pre-compilation complete")

    # Start LLM client warm-up in background (non-blocking)
    # This avoids blocking startup if LLM APIs are unavailable
    import asyncio

    async def warm_up_clients():
        """Run LLM client warm-up in the background."""
        from ansari_langgraph.client_provider import get_llm_with_tools
        from langchain_core.messages import HumanMessage

        logger.info("Warming up LLM clients in the background...")
        for model_id in config.MODELS.keys():
            try:
                logger.info(f"  - Warming up {model_id}...")
                client = get_llm_with_tools(model_id)
                # Make a trivial call to trigger client initialization
                await client.ainvoke([HumanMessage(content="test")])
                logger.info(f"  - {model_id} is warm")
            except Exception as e:
                # Log the error but don't block startup
                logger.error(f"  - Failed to warm up {model_id}: {e}", exc_info=True)
        logger.info("LLM client warm-up complete")

    # Start warm-up as a non-blocking background task
    asyncio.create_task(warm_up_clients())

    # Start background cleanup task
    await session_manager.start_cleanup_task()
    logger.info("Session cleanup task started")

    yield

    # Shutdown
    logger.info("Shutting down model comparison application...")
    await session_manager.stop_cleanup_task()
    logger.info("Session cleanup task stopped")


# Create FastAPI app
app = FastAPI(
    title="LLM Model Comparison",
    description="Compare multiple LLM models side-by-side",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API router
app.include_router(router)


@app.get("/")
async def index():
    """Serve the main HTML interface."""
    index_html_path = Path(__file__).parent / "index.html"
    return FileResponse(index_html_path)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    session_count = await session_manager.get_session_count()
    return JSONResponse(
        content={
            "status": "healthy",
            "session_count": session_count,
            "models": list(config.MODELS.keys()),
        }
    )


@app.get("/debug/memory")
async def debug_memory(username: str = Depends(verify_credentials)):
    """Debug endpoint to check memory usage (requires auth)."""
    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        session_count = await session_manager.get_session_count()

        return JSONResponse(
            content={
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "session_count": session_count,
            }
        )
    except ImportError:
        return JSONResponse(
            content={"error": "psutil not installed"},
            status_code=500,
        )


@app.get("/debug")
async def debug_ui(username: str = Depends(verify_credentials)):
    """Serve debug HTML interface (requires auth)."""
    debug_html_path = Path(__file__).parent / "debug.html"
    return FileResponse(debug_html_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
