"""Tools for Ansari LangGraph implementation."""

import httpx
from langchain_core.tools import tool
from ansari_agent.utils import config, setup_logger

logger = setup_logger(__name__)


@tool
async def search_quran(query: str) -> dict:
    """Search and retrieve relevant ayahs from the Quran based on a specific topic.

    Args:
        query: Topic or subject matter to search for within the Holy Quran.
               Make this as specific as possible. Do not include the word "quran" in the request.

    Returns:
        Dictionary with 'results' list containing ayah information with citations.
    """
    logger.info(f'Searching Quran for: "{query}"')

    # Prepare API request
    headers = {"x-api-key": config.KALIMAT_API_KEY}
    params = {
        "query": query,
        "numResults": 10,
        "getText": 1,  # 1 = Quran
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                config.KALEMAT_BASE_URL,
                headers=headers,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            results = response.json()

        logger.debug(f"Received {len(results)} results from Kalimat API")

        # Format results with full metadata
        formatted_results = []
        for result in results:
            ayah_id = result.get("id", "Unknown")
            arabic_text = result.get("text", "Not retrieved")
            english_text = result.get("en_text", "Not retrieved")

            formatted_results.append({
                "citation": ayah_id,
                "source_type": "quran",
                "arabic": arabic_text,
                "english": english_text,
                "query": query,
            })

        logger.info(f"Formatted {len(formatted_results)} ayahs")

        return {
            "results": formatted_results,
            "count": len(formatted_results),
            "query": query,
        }

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Kalimat API returned status {e.response.status_code}: {e.response.text}"
        )
        return {
            "results": [],
            "count": 0,
            "error": f"API error: {e.response.status_code}",
        }
    except Exception as e:
        logger.error(f"Error searching Quran: {str(e)}")
        return {
            "results": [],
            "count": 0,
            "error": str(e),
        }
