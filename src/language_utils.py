"""Language detection and prompt building utilities.

This module provides:
- Language detection for AI responses (English vs Spanish)
- Prompt enhancement with language instructions
- Language verification for quality control
"""

import re
from typing import Tuple, Optional

from lingua import Language, LanguageDetectorBuilder


# Build detector for supported languages only (lightweight)
# Uses minimum relative distance to require clear distinction
DETECTOR = LanguageDetectorBuilder.from_languages(
    Language.ENGLISH,
    Language.SPANISH
).with_minimum_relative_distance(0.25).build()


# Chess notation patterns to strip before language detection
# These are universal and shouldn't influence language detection
CHESS_NOTATION_PATTERNS = [
    r'\b[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#=]?[QRBN]?\b',  # Piece moves: Nf3, Bxe5, e8=Q
    r'\bO-O(-O)?\b',  # Castling: O-O, O-O-O
    r'\b\d+\.\s*',  # Move numbers: 1. 2. 15.
    r'\b[A-E]\d{2}\b',  # ECO codes: C50, B90
]


def _strip_chess_notation(text: str) -> str:
    """Remove chess notation from text before language detection.

    Chess notation is universal and doesn't indicate language,
    so we strip it to get more accurate language detection.
    """
    cleaned = text
    for pattern in CHESS_NOTATION_PATTERNS:
        cleaned = re.sub(pattern, ' ', cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def detect_response_language(text: str) -> Tuple[str, float]:
    """Detect language of AI response.

    Args:
        text: AI-generated response text

    Returns:
        Tuple of (language_code, confidence_score)
        - language_code: 'en' or 'es' or 'unknown'
        - confidence_score: 0.0 to 1.0
    """
    if not text:
        return 'unknown', 0.0

    # Strip chess notation which is language-neutral
    cleaned_text = _strip_chess_notation(text)

    # Need minimum text length for reliable detection
    if len(cleaned_text) < 20:
        return 'unknown', 0.0

    result = DETECTOR.detect_language_of(cleaned_text)

    if result == Language.ENGLISH:
        confidence = DETECTOR.compute_language_confidence(cleaned_text, Language.ENGLISH)
        return 'en', confidence
    elif result == Language.SPANISH:
        confidence = DETECTOR.compute_language_confidence(cleaned_text, Language.SPANISH)
        return 'es', confidence
    else:
        return 'unknown', 0.0


def is_language_correct(response_text: str, expected_lang: str) -> bool:
    """Check if response is in expected language.

    Returns True if:
    - Expected language is English (default, less strict)
    - Response is in expected language with >50% confidence
    - Response is too short to detect reliably (can't determine)

    Args:
        response_text: The AI-generated response
        expected_lang: Expected language code ('en' or 'es')

    Returns:
        True if language appears correct, False otherwise
    """
    if expected_lang == 'en':
        # English is the default, less strict checking
        # Most content is in English, so we don't flag false positives
        return True

    detected_lang, confidence = detect_response_language(response_text)

    if detected_lang == 'unknown':
        # Can't determine, assume correct
        return True

    return detected_lang == expected_lang and confidence > 0.5


def build_enhanced_prompt(
    question: str,
    target_lang: str,
    user_writes_in: Optional[str] = None
) -> str:
    """Build prompt with language instruction prepended.

    For non-English target languages, prepends a language instruction
    to ensure the AI responds in the correct language while preserving
    universal chess notation.

    Args:
        question: User's original question
        target_lang: Language code for response ('en', 'es')
        user_writes_in: Detected language of user's question (optional)

    Returns:
        Enhanced prompt with language instruction (or unchanged for English)
    """
    if target_lang == 'en':
        # No modification needed for English
        return question

    # Language-specific instructions
    LANGUAGE_INSTRUCTIONS = {
        'es': """[IMPORTANT: Respond in Spanish. Use the chess terminology from the glossary source. Keep all chess notation (Nf3, O-O, exd5) in standard algebraic notation - do not translate moves. Translate piece names when explaining: 'el caballo en f3' but notation stays 'Nf3'.]

"""
    }

    instruction = LANGUAGE_INSTRUCTIONS.get(target_lang, '')

    if not instruction:
        # Unsupported language, return unchanged
        return question

    # If user wrote in a different language, add context-aware instruction
    if user_writes_in and user_writes_in != target_lang and user_writes_in != 'unknown':
        lang_names = {'en': 'English', 'es': 'Spanish'}
        user_lang_name = lang_names.get(user_writes_in, user_writes_in)
        target_lang_name = lang_names.get(target_lang, target_lang)
        instruction += f"[Note: The user wrote in {user_lang_name} but prefers responses in {target_lang_name}.]\n\n"

    return instruction + question
