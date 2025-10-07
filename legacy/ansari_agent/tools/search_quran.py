"""SearchQuran tool - Claude Agent SDK implementation."""

import httpx
from claude_agent_sdk import tool
from ansari_agent.utils import config, setup_logger

logger = setup_logger(__name__)


@tool(
    name="search_quran",
    description="""Search and retrieve relevant ayahs based on a specific topic.
    Returns multiple ayahs when applicable.""",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": """Topic or subject matter to search for within the Holy Quran.
                Make this as specific as possible.
                Do not include the word quran in the request.

                Returns results both as tool results and as references for citations.""",
            }
        },
        "required": ["query"],
    },
)
async def search_quran(args: dict) -> dict:
    """Search Quran verses using Kalimat API.

    Args:
        args: Dictionary containing 'query' parameter

    Returns:
        Dictionary with content blocks, each containing verse text and metadata
    """
    query = args.get("query", "")
    num_results = args.get("num_results", 10)

    logger.info(f'Searching Quran for: "{query}"')

    # Prepare API request
    headers = {"x-api-key": config.KALIMAT_API_KEY}
    params = {
        "query": query,
        "numResults": num_results,
        "getText": 1,  # 1 = Quran
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                config.KALEMAT_BASE_URL, headers=headers, params=params, timeout=30.0
            )
            response.raise_for_status()
            results = response.json()

        logger.debug(f"Received {len(results)} results from Kalimat API")

        # Format results as content blocks with metadata
        content_blocks = []
        for result in results:
            ayah_id = result.get("id", "Unknown")
            arabic_text = result.get("text", "Not retrieved")
            english_text = result.get("en_text", "Not retrieved")

            # Create content block with embedded metadata
            content_blocks.append(
                {
                    "type": "text",
                    "text": f"""Ayah: {ayah_id}
Arabic Text: {arabic_text}

English Text: {english_text}
""",
                    "metadata": {
                        "citation": ayah_id,
                        "source_type": "quran",
                        "arabic": arabic_text,
                        "english": english_text,
                        "query": query,
                    },
                }
            )

        logger.info(f"Formatted {len(content_blocks)} content blocks")
        return {"content": content_blocks}

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Kalimat API returned status {e.response.status_code}: {e.response.text}"
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error searching Quran: API returned status {e.response.status_code}",
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error searching Quran: {str(e)}")
        return {
            "content": [
                {"type": "text", "text": f"Error searching Quran: {str(e)}"}
            ]
        }
