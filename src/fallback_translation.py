"""Fallback translation service client and incident logging.

This module provides:
- Translation of AI responses when language detection fails
- Incident logging for monitoring wrong-language responses
"""

from datetime import datetime

import httpx
import structlog

logger = structlog.get_logger()


# Phase 1 translation service URL
# Uses localhost for local development; Kubernetes uses service discovery
TRANSLATION_SERVICE_URL = "http://localhost:3035"


async def translate_response(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """Translate AI response using Phase 1 translation service.

    This is the fallback mechanism when the AI responds in the wrong
    language despite prompt instructions. Uses the chess glossary
    to ensure correct terminology.

    Args:
        text: Response text to translate
        source_lang: Detected source language ('en' or 'es')
        target_lang: User's preferred language ('en' or 'es')

    Returns:
        Translated text, or original if translation fails (graceful degradation)
    """
    if source_lang == target_lang:
        return text

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TRANSLATION_SERVICE_URL}/translate",
                json={
                    "text": text,
                    "source": source_lang,
                    "target": target_lang,
                    "use_glossary": True  # Apply chess glossary corrections
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("translated", text)
    except httpx.TimeoutException:
        logger.warning(
            "Translation service timeout",
            source_lang=source_lang,
            target_lang=target_lang,
            text_length=len(text)
        )
        return text  # Return original on timeout
    except httpx.HTTPStatusError as e:
        logger.error(
            "Translation service HTTP error",
            status_code=e.response.status_code,
            source_lang=source_lang,
            target_lang=target_lang
        )
        return text  # Return original on HTTP error
    except Exception as e:
        logger.error(
            "Fallback translation failed",
            error=str(e),
            source_lang=source_lang,
            target_lang=target_lang
        )
        return text  # Return original on any failure


async def log_language_incident(
    user_email: str,
    expected_lang: str,
    detected_lang: str,
    question: str,
    response_preview: str
) -> None:
    """Log when AI responds in wrong language for monitoring.

    This is a fire-and-forget logging function that helps identify:
    - Questions that confuse the language instruction
    - Patterns in language failures
    - Whether prompt improvements are needed

    Args:
        user_email: User identifier (for aggregation)
        expected_lang: Language the user expected
        detected_lang: Language that was detected in response
        question: The original question (truncated for logging)
        response_preview: Preview of the response (truncated)
    """
    # Truncate previews to avoid log bloat
    question_preview = question[:100] if question else None
    response_truncated = response_preview[:100] if response_preview else None

    logger.warning(
        "AI responded in wrong language",
        user_email=user_email,
        expected_lang=expected_lang,
        detected_lang=detected_lang,
        question_preview=question_preview,
        response_preview=response_truncated,
        timestamp=datetime.utcnow().isoformat()
    )

    # Note: Could extend this to store in MongoDB for analytics
    # For now, structlog warning is sufficient for monitoring
    # Future: await db.language_incidents.insert_one({...})
