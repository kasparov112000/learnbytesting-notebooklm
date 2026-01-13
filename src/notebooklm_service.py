"""NotebookLM service wrapper for interacting with Google NotebookLM."""

from typing import Optional, List, Any
from datetime import datetime
import structlog

# NotebookLM-py imports
try:
    from notebooklm import NotebookLMClient
    NOTEBOOKLM_AVAILABLE = True
except ImportError:
    NOTEBOOKLM_AVAILABLE = False
    NotebookLMClient = None

from .config import settings
from .models import (
    UserNotebook,
    NotebookSource,
    SourceType,
    AskQuestionResponse,
    GenerateContentResponse,
    SaveNoteResponse,
)
from .database import db

logger = structlog.get_logger()


class NotebookLMService:
    """Service for interacting with NotebookLM."""

    def __init__(self):
        self._authenticated = False

    async def check_auth(self) -> bool:
        """Check if NotebookLM is authenticated."""
        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available - library not installed")
            return False
        try:
            logger.info("Checking NotebookLM authentication...")
            async with await NotebookLMClient.from_storage() as client:
                notebooks = await client.notebooks.list()
                self._authenticated = True
                logger.info("NotebookLM auth successful", notebook_count=len(notebooks))
                return True
        except Exception as e:
            import traceback
            logger.error("NotebookLM auth check failed", error=str(e), error_type=type(e).__name__, traceback=traceback.format_exc())
            self._authenticated = False
            return False

    @property
    def is_authenticated(self) -> bool:
        """Check if NotebookLM is authenticated."""
        return self._authenticated

    async def get_or_create_notebook(
        self,
        user_email: str,
        notebook_name: Optional[str] = None
    ) -> Optional[UserNotebook]:
        """Get existing notebook or create new one for user."""

        # Check if user already has a notebook
        existing = await db.get_user_notebook(user_email)
        if existing:
            logger.info("Found existing notebook", user_email=user_email, notebook_id=existing.notebook_id)
            return existing

        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return None

        name = notebook_name or f"Chess Learning - {user_email}"

        try:
            async with await NotebookLMClient.from_storage() as client:
                # Create notebook in NotebookLM
                notebook = await client.notebooks.create(title=name)

                user_notebook = UserNotebook(
                    user_email=user_email,
                    notebook_id=notebook.id,
                    notebook_name=name,
                    sources=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                # Save mapping to database
                await db.save_user_notebook(user_notebook)

                logger.info("Created new notebook", user_email=user_email, notebook_id=notebook.id)
                return user_notebook

        except Exception as e:
            logger.error("Failed to create notebook", error=str(e), user_email=user_email)
            return None

    async def add_source(
        self,
        user_email: str,
        source_type: SourceType,
        content: str,
        title: Optional[str] = None
    ) -> bool:
        """Add a source to user's notebook."""

        user_notebook = await db.get_user_notebook(user_email)
        if not user_notebook:
            logger.error("No notebook found for user", user_email=user_email)
            return False

        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return False

        try:
            async with await NotebookLMClient.from_storage() as client:
                notebook_id = user_notebook.notebook_id

                # Add source based on type
                if source_type == SourceType.URL:
                    await client.sources.add_url(notebook_id, url=content)
                elif source_type == SourceType.TEXT:
                    await client.sources.add_text(notebook_id, title=title or "Pasted Text", content=content)
                elif source_type == SourceType.YOUTUBE:
                    await client.sources.add_url(notebook_id, url=content)
                else:
                    logger.error("Unsupported source type", source_type=source_type)
                    return False

                # Record source in database
                source = NotebookSource(
                    source_type=source_type,
                    content=content,
                    title=title,
                    added_at=datetime.utcnow()
                )
                await db.add_source_to_notebook(user_email, source)

                logger.info("Added source to notebook", user_email=user_email, source_type=source_type)
                return True

        except Exception as e:
            logger.error("Failed to add source", error=str(e), user_email=user_email)
            return False

    async def add_chess_game(
        self,
        user_email: str,
        pgn: str,
        game_title: Optional[str] = None,
        analysis: Optional[str] = None
    ) -> bool:
        """Add a chess game (PGN + analysis) to user's notebook."""

        # Format the game content
        content_parts = [f"# Chess Game: {game_title or 'Game Analysis'}\n"]
        content_parts.append("## PGN Notation\n```\n" + pgn + "\n```\n")

        if analysis:
            content_parts.append("## Analysis\n" + analysis + "\n")

        content = "\n".join(content_parts)

        return await self.add_source(
            user_email=user_email,
            source_type=SourceType.TEXT,
            content=content,
            title=game_title or "Chess Game"
        )

    async def save_note(
        self,
        user_email: str,
        content: str,
        title: Optional[str] = None,
        notebook_name: Optional[str] = None
    ) -> SaveNoteResponse:
        """Save a note to user's notebook, creating notebook if needed."""

        notebook_created = False

        # Check if user has a notebook
        user_notebook = await db.get_user_notebook(user_email)

        if not user_notebook:
            # Create notebook for user
            user_notebook = await self.get_or_create_notebook(
                user_email=user_email,
                notebook_name=notebook_name
            )
            if user_notebook:
                notebook_created = True
            else:
                return SaveNoteResponse(
                    success=False,
                    notebook_id="",
                    notebook_name="",
                    notebook_created=False,
                    message="Failed to create notebook. Check if NotebookLM is authenticated."
                )

        # Add the note as a source
        success = await self.add_source(
            user_email=user_email,
            source_type=SourceType.TEXT,
            content=content,
            title=title
        )

        if success:
            return SaveNoteResponse(
                success=True,
                notebook_id=user_notebook.notebook_id,
                notebook_name=user_notebook.notebook_name,
                notebook_created=notebook_created,
                message=f"Note saved successfully{' (new notebook created)' if notebook_created else ''}"
            )
        else:
            return SaveNoteResponse(
                success=False,
                notebook_id=user_notebook.notebook_id,
                notebook_name=user_notebook.notebook_name,
                notebook_created=notebook_created,
                message="Failed to save note to NotebookLM"
            )

    async def ask_question(
        self,
        user_email: str,
        question: str,
        conversation_id: Optional[str] = None
    ) -> Optional[AskQuestionResponse]:
        """Ask a question to user's notebook (RAG inference)."""

        user_notebook = await db.get_user_notebook(user_email)
        if not user_notebook:
            logger.error("No notebook found for user", user_email=user_email)
            return None

        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return None

        try:
            async with await NotebookLMClient.from_storage() as client:
                # Query the notebook using chat.ask
                response = await client.chat.ask(
                    notebook_id=user_notebook.notebook_id,
                    question=question
                )

                return AskQuestionResponse(
                    answer=response.answer if hasattr(response, 'answer') else str(response),
                    sources_used=[],
                    conversation_id=response.conversation_id if hasattr(response, 'conversation_id') else conversation_id
                )

        except Exception as e:
            import traceback
            logger.error("Failed to ask question", error=str(e), error_type=type(e).__name__, user_email=user_email, traceback=traceback.format_exc())
            return None

    async def generate_content(
        self,
        user_email: str,
        content_type: str,
        topic: Optional[str] = None
    ) -> Optional[GenerateContentResponse]:
        """Generate content (podcast, quiz, flashcards) from notebook."""

        user_notebook = await db.get_user_notebook(user_email)
        if not user_notebook:
            logger.error("No notebook found for user", user_email=user_email)
            return None

        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return None

        try:
            async with await NotebookLMClient.from_storage() as client:
                notebook_id = user_notebook.notebook_id

                if content_type == "podcast":
                    result = await client.artifacts.generate_audio(notebook_id)
                elif content_type == "quiz":
                    result = await client.artifacts.generate_quiz(notebook_id)
                else:
                    logger.error("Unknown content type", content_type=content_type)
                    return None

                return GenerateContentResponse(
                    task_id=str(result.id) if hasattr(result, 'id') else "unknown",
                    status="processing"
                )

        except Exception as e:
            logger.error("Failed to generate content", error=str(e), user_email=user_email)
            return None

    async def list_notebooks(self) -> List[dict]:
        """List all notebooks in NotebookLM account."""
        if not NOTEBOOKLM_AVAILABLE:
            return []

        try:
            async with await NotebookLMClient.from_storage() as client:
                notebooks = await client.notebooks.list()
                return [{"id": n.id, "name": n.title} for n in notebooks]
        except Exception as e:
            logger.error("Failed to list notebooks", error=str(e))
            return []

    async def delete_notebook(self, user_email: str) -> bool:
        """Delete user's notebook."""

        user_notebook = await db.get_user_notebook(user_email)
        if not user_notebook:
            return False

        if not NOTEBOOKLM_AVAILABLE:
            return False

        try:
            async with await NotebookLMClient.from_storage() as client:
                await client.notebooks.delete(user_notebook.notebook_id)

            await db.delete_user_notebook(user_email)

            logger.info("Deleted notebook", user_email=user_email)
            return True

        except Exception as e:
            logger.error("Failed to delete notebook", error=str(e), user_email=user_email)
            return False


# Global service instance
notebooklm_service = NotebookLMService()
