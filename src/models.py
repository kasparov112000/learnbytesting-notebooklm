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


class NotebookSource(BaseModel):
    """A source added to a notebook."""
    source_id: Optional[str] = None
    source_type: SourceType
    content: str  # URL, file path, or text content
    title: Optional[str] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)


class UserNotebook(BaseModel):
    """Mapping between user email and their NotebookLM notebook."""
    user_email: str
    notebook_id: str
    notebook_name: str
    sources: List[NotebookSource] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CreateNotebookRequest(BaseModel):
    """Request to create or get a notebook for a user."""
    user_email: str
    notebook_name: Optional[str] = None  # Auto-generated if not provided


class AddSourceRequest(BaseModel):
    """Request to add a source to a user's notebook."""
    user_email: str
    source_type: SourceType
    content: str
    title: Optional[str] = None


class AddChessGameRequest(BaseModel):
    """Request to add a chess game to a user's notebook."""
    user_email: str
    pgn: str  # PGN notation of the game
    game_title: Optional[str] = None
    analysis: Optional[str] = None  # Optional analysis from chess-ai


class AskQuestionRequest(BaseModel):
    """Request to ask a question to the user's notebook."""
    user_email: str
    question: str
    conversation_id: Optional[str] = None  # For maintaining context


class AskQuestionResponse(BaseModel):
    """Response from asking a question."""
    answer: str
    sources_used: List[str] = []
    conversation_id: Optional[str] = None


class GenerateContentRequest(BaseModel):
    """Request to generate content from the notebook."""
    user_email: str
    content_type: str  # "podcast", "quiz", "flashcards", "summary"
    topic: Optional[str] = None


class GenerateContentResponse(BaseModel):
    """Response from content generation."""
    task_id: str
    status: str
    content_url: Optional[str] = None


class NotebookInfo(BaseModel):
    """Information about a user's notebook."""
    user_email: str
    notebook_id: str
    notebook_name: str
    source_count: int
    created_at: datetime
    updated_at: datetime


class SaveNoteRequest(BaseModel):
    """Request to save a note (creates notebook if needed)."""
    user_email: str
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
