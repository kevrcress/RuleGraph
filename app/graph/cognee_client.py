"""
Cognee knowledge graph client.
CRITICAL: ALL Cognee calls must go through this module only.
No other file in the application may import or call cognee directly.
"""
import logging
import pathlib

logger = logging.getLogger(__name__)

_SKILLS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "my_skills"

_cognee_available = False

try:
    import cognee
    _cognee_available = True
except ImportError:
    logger.warning("cognee package not available — graph enrichment disabled")


async def init_cognee(db=None) -> None:
    """Initialize Cognee LLM provider.

    When a DB session is provided, reads litellm_base_url and complex_model from
    admin settings so Cognee can route through the LiteLLM proxy if configured.
    """
    if not _cognee_available:
        logger.warning("Cognee not available, skipping initialization")
        return
    try:
        from app.config import settings as _cfg

        base_url = _cfg.litellm_base_url
        model = _cfg.complex_model

        if db is not None:
            from app.services.settings_service import get_litellm_base_url, get_complex_model
            base_url = await get_litellm_base_url(db) or base_url
            model = await get_complex_model(db) or model

        if base_url:
            # Route Cognee through the LiteLLM proxy using the OpenAI-compatible endpoint.
            # LiteLLM exposes /v1 which cognee's openai provider can reach.
            cognee.config.set_llm_provider("openai")
            cognee.config.set_llm_endpoint(base_url.rstrip("/") + "/v1")
            cognee.config.set_llm_api_key("litellm")
            cognee.config.set_llm_model(model)
            logger.info("Cognee initialized via LiteLLM proxy at %s (model: %s)", base_url, model)
        else:
            cognee.config.set_llm_provider("anthropic")
            cognee.config.set_llm_model(model)
            # cognee uses ANTHROPIC_API_KEY from environment automatically
            logger.info("Cognee initialized with Anthropic provider (model: %s)", model)
    except Exception as e:
        # Cognee init failure must never crash the application
        logger.warning(f"Cognee initialization failed (graph enrichment will be disabled): {e}")


async def add_to_graph(content: str, dataset_name: str = "rulegraph", db=None) -> str | None:
    """
    Add content to knowledge graph. Returns node ID or None on failure.

    Cognee failures are logged to application logs but NOT to the ingest_errors
    table. Cognee is best-effort graph enrichment; the canonical data store is
    Postgres. See DECISIONS.md for rationale.
    """
    if not _cognee_available:
        return None
    if db is not None:
        from app.services.settings_service import is_claude_enabled
        if not await is_claude_enabled(db):
            logger.info("Claude API disabled by admin — skipping Cognee graph enrichment")
            return None
        # Close the implicit read transaction before the Cognee call — Cognee runs
        # its own LLM internally and can take >30s, which would trip
        # idle_in_transaction_session_timeout and kill the connection.
        await db.commit()
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


async def cognify_graph(dataset_name: str = "rulegraph") -> None:
    """
    Re-process ingested data into a richer knowledge graph structure.
    Called by /lint to improve graph quality after new data is ingested.
    """
    if not _cognee_available:
        logger.info("Cognee not available — skipping cognify")
        return
    try:
        await cognee.cognify(datasets=dataset_name)
        logger.info("Cognee cognify complete for dataset '%s'", dataset_name)
    except Exception as exc:
        logger.warning("Cognee cognify failed (non-fatal): %s", exc)


async def ingest_skills() -> None:
    """Ingest all skill files from my_skills/ into Cognee at startup."""
    if not _cognee_available:
        logger.info("Cognee not available — skipping skill ingestion")
        return
    if not _SKILLS_DIR.exists():
        logger.warning("my_skills/ directory not found — skipping skill ingestion")
        return
    for skill_file in _SKILLS_DIR.glob("*.md"):
        try:
            content = skill_file.read_text(encoding="utf-8")
            await cognee.add(content, "rulegraph_skills")
            logger.info("Ingested skill: %s", skill_file.name)
        except Exception as exc:
            logger.warning("Failed to ingest skill %s (non-fatal): %s", skill_file.name, exc)


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
