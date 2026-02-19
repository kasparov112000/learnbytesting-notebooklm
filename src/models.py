"""Pydantic models for NotebookLM Microservice."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Types of sources that can be added to a notebook."""
    URL = "url"
    FILE = "file"
    TEXT = "text"
    YOUTUBE = "youtube"


def make_user_key(user_email: str, main_category: str) -> str:
    """Create a user key from email and main category.

    Format: "email-mainCategory" (e.g., "user@example.com-chess")
    """
    return f"{user_email}-{main_category}"


def parse_user_key(user_key: str) -> tuple[str, str]:
    """Parse a user key into email and main category.

    Returns: (user_email, main_category)
    Raises: ValueError if format is invalid
    """
    # Split on the last hyphen to handle emails with hyphens
    parts = user_key.rsplit('-', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid user_key format: {user_key}")
    return parts[0], parts[1]


class NotebookSource(BaseModel):
    """A source added to a notebook."""
    source_id: Optional[str] = None
    source_type: SourceType
    content: str  # URL, file path, or text content
    title: Optional[str] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)


class UserNotebook(BaseModel):
    """Mapping between user (email + category) and their NotebookLM notebook."""
    user_key: str  # Format: "email-mainCategory" (e.g., "user@example.com-chess")
    user_email: str  # Keep for reference
    main_category: str  # The category this notebook is for
    notebook_id: str
    notebook_name: str
    preferred_language: str = "en"  # User's preferred response language ('en', 'es')
    glossary_version: str = "1.0"  # Track glossary source version for future updates
    sources: List[NotebookSource] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CreateNotebookRequest(BaseModel):
    """Request to create or get a notebook for a user."""
    user_email: str
    main_category: str = "chess"  # Default to chess for backward compatibility
    notebook_name: Optional[str] = None  # Auto-generated if not provided
    preferred_language: str = "en"  # User's preferred response language ('en', 'es')


class AddSourceRequest(BaseModel):
    """Request to add a source to a user's notebook."""
    user_email: str
    main_category: str = "chess"  # Default to chess for backward compatibility
    source_type: SourceType
    content: str
    title: Optional[str] = None


class AddChessGameRequest(BaseModel):
    """Request to add a chess game to a user's notebook."""
    user_email: str
    main_category: str = "chess"  # Default to chess for backward compatibility
    pgn: str  # PGN notation of the game
    game_title: Optional[str] = None
    analysis: Optional[str] = None  # Optional analysis from chess-ai


class AskQuestionRequest(BaseModel):
    """Request to ask a question to the user's notebook."""
    user_email: str
    main_category: str = "chess"  # Default to chess for backward compatibility
    question: str
    preferred_language: str = "en"  # User's preferred response language ('en', 'es')
    conversation_id: Optional[str] = None  # For maintaining context


class AskQuestionResponse(BaseModel):
    """Response from asking a question."""
    answer: str
    sources_used: List[str] = []
    conversation_id: Optional[str] = None
    response_language: str = "en"  # Language of the response
    was_translated: bool = False  # Whether fallback translation was applied


class GenerateContentRequest(BaseModel):
    """Request to generate content from the notebook."""
    user_email: str
    main_category: str = "chess"  # Default to chess for backward compatibility
    content_type: str  # "podcast", "quiz", "flashcards", "summary"
    topic: Optional[str] = None


class GenerateContentResponse(BaseModel):
    """Response from content generation."""
    task_id: str
    status: str
    content_url: Optional[str] = None


class NotebookInfo(BaseModel):
    """Information about a user's notebook."""
    user_key: str  # Format: "email-mainCategory"
    user_email: str
    main_category: str
    notebook_id: str
    notebook_name: str
    source_count: int
    created_at: datetime
    updated_at: datetime


class SaveNoteRequest(BaseModel):
    """Request to save a note (creates notebook if needed)."""
    user_email: str
    main_category: str = "chess"  # Default to chess for backward compatibility
    content: str
    title: Optional[str] = None
    notebook_name: Optional[str] = None  # Name for new notebook if created


class SaveNoteResponse(BaseModel):
    """Response from saving a note."""
    success: bool
    notebook_id: str
    notebook_name: str
    notebook_created: bool  # True if notebook was just created
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    notebooklm_authenticated: bool


# ============================================================================
# Analysis History Models
# ============================================================================

class AnalysisRecord(BaseModel):
    """A single analysis query and response."""
    analysis_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()).replace('.', ''))
    question: str
    answer: str
    sources_used: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SaveAnalysisRequest(BaseModel):
    """Request to save an analysis to history."""
    user_email: str
    main_category: str = "chess"  # Default to chess for backward compatibility
    question: str
    answer: str
    sources_used: List[str] = []


class SaveAnalysisResponse(BaseModel):
    """Response from saving an analysis."""
    success: bool
    analysis_id: str
    message: str


class AnalysisHistoryResponse(BaseModel):
    """Response containing analysis history."""
    user_key: str  # Format: "email-mainCategory"
    user_email: str
    main_category: str
    analyses: List[AnalysisRecord] = []
    total_count: int


# ============================================================================
# LearnByTesting.ai Dedicated Notebook Models
# ============================================================================

class LBTAddSourceRequest(BaseModel):
    """Request to add a source to the LBT notebook."""
    source_type: SourceType
    content: str
    title: Optional[str] = None


class LBTAskRequest(BaseModel):
    """Request to ask a question to the LBT notebook."""
    question: str
    conversation_id: Optional[str] = None


class LBTAskResponse(BaseModel):
    """Response from asking a question to the LBT notebook."""
    answer: str
    sources_used: List[str] = []
    conversation_id: Optional[str] = None
    notebook_id: str


class LBTNotebookInfoResponse(BaseModel):
    """Information about the LBT notebook."""
    notebook_id: str
    notebook_name: str
    source_count: int
    is_available: bool
    message: str


class LBTSourceListResponse(BaseModel):
    """List of sources in the LBT notebook."""
    notebook_id: str
    sources: List[dict] = []
    count: int
