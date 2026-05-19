"""
Cognee knowledge graph client.
CRITICAL: ALL Cognee calls must go through this module only.
No other file in the application may import or call cognee directly.
"""
import logging

logger = logging.getLogger(__name__)

_cognee_available = False

try:
    import cognee
    _cognee_available = True
except ImportError:
    logger.warning("cognee package not available — graph enrichment disabled")


async def init_cognee() -> None:
    """Initialize cognee with Anthropic LLM provider."""
    if not _cognee_available:
        logger.warning("Cognee not available, skipping initialization")
        return
    try:
        cognee.config.set_llm_provider("anthropic")
        cognee.config.set_llm_model("claude-sonnet-4-5")
        # cognee uses ANTHROPIC_API_KEY from environment automatically
        logger.info("Cognee initialized with Anthropic provider")
    except Exception as e:
        # Cognee init failure must never crash the application
        logger.warning(f"Cognee initialization failed (graph enrichment will be disabled): {e}")


async def add_to_graph(content: str, dataset_name: str = "rulegraph") -> str | None:
    """
    Add content to knowledge graph. Returns node ID or None on failure.

    Cognee failures are logged to application logs but NOT to the ingest_errors
    table. Cognee is best-effort graph enrichment; the canonical data store is
    Postgres. See DECISIONS.md for rationale.
    """
    if not _cognee_available:
        return None
    try:
        await cognee.add(content, dataset_name)
        # cognify may not exist in all versions of cognee 0.1.15
        try:
            await cognee.cognify()
        except AttributeError:
            pass  # cognify not available in this version
        return dataset_name  # use as node reference
    except Exception as e:
        # Log but do not raise — Cognee failure must not fail the ingest pipeline
        logger.warning(f"Cognee add_to_graph failed (non-fatal): {e}")
        return None


async def search_graph(query: str) -> list:
    """Search the knowledge graph."""
    if not _cognee_available:
        return []
    try:
        results = await cognee.search(query)
        return results or []
    except Exception as e:
        logger.warning(f"Cognee search_graph failed: {e}")
        return []


async def recall_from_graph(query: str) -> list:
    """
    Recall context from graph.
    Falls back to cognee.search() if cognee.recall() is not available in 0.1.15.
    """
    if not _cognee_available:
        return []
    try:
        results = await cognee.recall(query)
        return results or []
    except AttributeError:
        # recall() may not exist in cognee 0.1.15 — fall back to search
        try:
            results = await cognee.search(query)
            return results or []
        except Exception as e:
            logger.warning(f"Cognee recall_from_graph (search fallback) failed: {e}")
            return []
    except Exception as e:
        logger.warning(f"Cognee recall_from_graph failed: {e}")
        return []
