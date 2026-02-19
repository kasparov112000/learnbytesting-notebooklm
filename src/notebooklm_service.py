"""NotebookLM service wrapper for interacting with Google NotebookLM."""

import asyncio
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
    make_user_key,
)
from .database import db

# Language handling utilities from Phase 4
from .language_utils import build_enhanced_prompt, detect_response_language, is_language_correct
from .glossary_source import add_glossary_source_to_notebook
from .fallback_translation import translate_response, log_language_incident

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
        main_category: str,
        notebook_name: Optional[str] = None,
        preferred_language: str = 'en'
    ) -> Optional[UserNotebook]:
        """Get existing notebook or create new one for user.

        Args:
            user_email: User's email address
            main_category: Category for the notebook (e.g., 'chess')
            notebook_name: Optional custom notebook name
            preferred_language: User's preferred response language ('en', 'es')

        Returns:
            UserNotebook if found or created, None on failure
        """
        user_key = make_user_key(user_email, main_category)

        # Check if user already has a notebook
        existing = await db.get_user_notebook(user_key)
        if existing:
            logger.info("Found existing notebook", user_key=user_key, notebook_id=existing.notebook_id)
            return existing

        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return None

        name = notebook_name or f"Chess Learning - {user_email} ({main_category})"

        try:
            async with await NotebookLMClient.from_storage() as client:
                # Create notebook in NotebookLM
                notebook = await client.notebooks.create(title=name)

                # Add glossary source for non-English users
                if preferred_language != 'en':
                    try:
                        await add_glossary_source_to_notebook(client, notebook.id, preferred_language)
                        logger.info("Added glossary source to notebook", user_key=user_key, language=preferred_language)
                    except Exception as e:
                        logger.warning("Failed to add glossary source", error=str(e), user_key=user_key)
                        # Continue anyway - glossary is nice-to-have

                user_notebook = UserNotebook(
                    user_key=user_key,
                    user_email=user_email,
                    main_category=main_category,
                    notebook_id=notebook.id,
                    notebook_name=name,
                    preferred_language=preferred_language,
                    sources=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                # Save mapping to database
                await db.save_user_notebook(user_notebook)

                logger.info("Created new notebook", user_key=user_key, notebook_id=notebook.id, preferred_language=preferred_language)
                return user_notebook

        except Exception as e:
            logger.error("Failed to create notebook", error=str(e), user_key=user_key)
            return None

    async def add_source(
        self,
        user_email: str,
        main_category: str,
        source_type: SourceType,
        content: str,
        title: Optional[str] = None,
        auto_create_notebook: bool = True,
        preferred_language: str = 'en'
    ) -> bool:
        """Add a source to user's notebook. Creates notebook if it doesn't exist."""
        user_key = make_user_key(user_email, main_category)

        user_notebook = await db.get_user_notebook(user_key)
        if not user_notebook:
            if auto_create_notebook:
                logger.info("No notebook found, creating one", user_key=user_key)
                user_notebook = await self.get_or_create_notebook(
                    user_email=user_email,
                    main_category=main_category,
                    preferred_language=preferred_language
                )
                if not user_notebook:
                    logger.error("Failed to create notebook for user", user_key=user_key)
                    return False
            else:
                logger.error("No notebook found for user", user_key=user_key)
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
                await db.add_source_to_notebook(user_key, source)

                logger.info("Added source to notebook", user_key=user_key, source_type=source_type)
                return True

        except Exception as e:
            logger.error("Failed to add source", error=str(e), user_key=user_key)
            return False

    async def add_chess_game(
        self,
        user_email: str,
        main_category: str,
        pgn: str,
        game_title: Optional[str] = None,
        analysis: Optional[str] = None
    ) -> bool:
        """Add a chess game (PGN + analysis) to user's notebook.

        This method ensures the notebook exists and is valid before adding the game.
        If the notebook is stale (exists in DB but not in NotebookLM), it will be recreated.
        """
        user_key = make_user_key(user_email, main_category)

        # Format the game content
        content_parts = [f"# Chess Game: {game_title or 'Game Analysis'}\n"]
        content_parts.append("## PGN Notation\n```\n" + pgn + "\n```\n")

        if analysis:
            content_parts.append("## Analysis\n" + analysis + "\n")

        content = "\n".join(content_parts)

        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return False

        # Get or create the notebook, verifying it exists in NotebookLM
        user_notebook = await self._ensure_valid_notebook(user_email, main_category)
        if not user_notebook:
            logger.error("Failed to ensure valid notebook", user_key=user_key)
            return False

        try:
            async with await NotebookLMClient.from_storage() as client:
                # Add the chess game as a text source
                await client.sources.add_text(
                    user_notebook.notebook_id,
                    title=game_title or "Chess Game",
                    content=content
                )

                # Record source in database
                source = NotebookSource(
                    source_type=SourceType.TEXT,
                    content=content[:500],  # Store preview only
                    title=game_title,
                    added_at=datetime.utcnow()
                )
                await db.add_source_to_notebook(user_key, source)

                logger.info("Added chess game to notebook", user_key=user_key, title=game_title)
                return True

        except Exception as e:
            logger.error("Failed to add chess game", error=str(e), user_key=user_key)
            return False

    async def _ensure_valid_notebook(
        self,
        user_email: str,
        main_category: str,
        preferred_language: str = 'en'
    ) -> Optional[UserNotebook]:
        """Ensure the user has a valid notebook that exists in NotebookLM.

        If the notebook exists in DB but not in NotebookLM (stale), delete and recreate it.
        """
        user_key = make_user_key(user_email, main_category)

        # Check if user has a notebook in database
        user_notebook = await db.get_user_notebook(user_key)

        if user_notebook:
            # Verify the notebook still exists in NotebookLM
            try:
                async with await NotebookLMClient.from_storage() as client:
                    await client.notebooks.get(user_notebook.notebook_id)
                    logger.info("Verified notebook exists", user_key=user_key, notebook_id=user_notebook.notebook_id)
                    return user_notebook
            except Exception as e:
                # Notebook doesn't exist in NotebookLM anymore - delete stale record
                logger.warning(
                    "Notebook not found in NotebookLM, will recreate",
                    user_key=user_key,
                    notebook_id=user_notebook.notebook_id,
                    error=str(e)
                )
                await db.delete_user_notebook(user_key)

        # Create a new notebook
        logger.info("Creating new notebook", user_key=user_key)
        return await self.get_or_create_notebook(
            user_email=user_email,
            main_category=main_category,
            preferred_language=preferred_language
        )

    async def save_note(
        self,
        user_email: str,
        main_category: str,
        content: str,
        title: Optional[str] = None,
        notebook_name: Optional[str] = None,
        preferred_language: str = 'en'
    ) -> SaveNoteResponse:
        """Save a note to user's notebook, creating notebook if needed."""
        user_key = make_user_key(user_email, main_category)

        notebook_created = False

        # Check if user has a notebook
        user_notebook = await db.get_user_notebook(user_key)

        if not user_notebook:
            # Create notebook for user
            user_notebook = await self.get_or_create_notebook(
                user_email=user_email,
                main_category=main_category,
                notebook_name=notebook_name,
                preferred_language=preferred_language
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

        # Add the note as a source (notebook already exists at this point)
        success = await self.add_source(
            user_email=user_email,
            main_category=main_category,
            source_type=SourceType.TEXT,
            content=content,
            title=title,
            auto_create_notebook=False  # Already handled above
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
        main_category: str,
        question: str,
        preferred_language: str = 'en',
        conversation_id: Optional[str] = None,
        auto_create_notebook: bool = True
    ) -> Optional[AskQuestionResponse]:
        """Ask a question to user's notebook (RAG inference). Creates notebook if it doesn't exist.

        Args:
            user_email: User's email address
            main_category: Category for the notebook (e.g., 'chess')
            question: The question to ask
            preferred_language: User's preferred response language ('en', 'es')
            conversation_id: Optional conversation ID for context
            auto_create_notebook: Whether to create notebook if it doesn't exist

        Returns:
            AskQuestionResponse with answer, language metadata, and translation status
        """
        user_key = make_user_key(user_email, main_category)

        user_notebook = await db.get_user_notebook(user_key)
        if not user_notebook:
            if auto_create_notebook:
                logger.info("No notebook found, creating one", user_key=user_key)
                user_notebook = await self.get_or_create_notebook(
                    user_email=user_email,
                    main_category=main_category,
                    preferred_language=preferred_language
                )
                if not user_notebook:
                    logger.error("Failed to create notebook for user", user_key=user_key)
                    return None
            else:
                logger.error("No notebook found for user", user_key=user_key)
                return None

        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return None

        try:
            async with await NotebookLMClient.from_storage() as client:
                # Detect question language for context
                question_lang, _ = detect_response_language(question)

                # Build enhanced prompt with language instruction
                enhanced_question = build_enhanced_prompt(
                    question=question,
                    target_lang=preferred_language,
                    user_writes_in=question_lang if question_lang != 'unknown' else None
                )

                logger.debug(
                    "Asking question with language handling",
                    user_key=user_key,
                    preferred_language=preferred_language,
                    question_lang=question_lang,
                    enhanced=enhanced_question != question
                )

                # Query the notebook using chat.ask
                response = await client.chat.ask(
                    notebook_id=user_notebook.notebook_id,
                    question=enhanced_question
                )

                answer = response.answer if hasattr(response, 'answer') else str(response)
                was_translated = False

                # Check if response is in expected language (only for non-English)
                if preferred_language != 'en':
                    if not is_language_correct(answer, preferred_language):
                        detected_lang, _ = detect_response_language(answer)

                        # Log incident for monitoring (fire-and-forget)
                        asyncio.create_task(log_language_incident(
                            user_email=user_email,
                            expected_lang=preferred_language,
                            detected_lang=detected_lang,
                            question=question,
                            response_preview=answer
                        ))

                        # Apply fallback translation
                        source_lang = detected_lang if detected_lang != 'unknown' else 'en'
                        answer = await translate_response(
                            text=answer,
                            source_lang=source_lang,
                            target_lang=preferred_language
                        )
                        was_translated = True

                        logger.info(
                            "Applied fallback translation",
                            user_key=user_key,
                            source_lang=source_lang,
                            target_lang=preferred_language
                        )

                return AskQuestionResponse(
                    answer=answer,
                    sources_used=[],
                    conversation_id=response.conversation_id if hasattr(response, 'conversation_id') else conversation_id,
                    response_language=preferred_language,
                    was_translated=was_translated
                )

        except Exception as e:
            import traceback
            logger.error("Failed to ask question", error=str(e), error_type=type(e).__name__, user_key=user_key, traceback=traceback.format_exc())
            return None

    async def generate_content(
        self,
        user_email: str,
        main_category: str,
        content_type: str,
        topic: Optional[str] = None
    ) -> Optional[GenerateContentResponse]:
        """Generate content (podcast, quiz, flashcards) from notebook."""
        user_key = make_user_key(user_email, main_category)

        user_notebook = await db.get_user_notebook(user_key)
        if not user_notebook:
            logger.error("No notebook found for user", user_key=user_key)
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
            logger.error("Failed to generate content", error=str(e), user_key=user_key)
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

    async def delete_notebook(self, user_email: str, main_category: str) -> bool:
        """Delete user's notebook."""
        user_key = make_user_key(user_email, main_category)

        user_notebook = await db.get_user_notebook(user_key)
        if not user_notebook:
            return False

        if not NOTEBOOKLM_AVAILABLE:
            return False

        try:
            async with await NotebookLMClient.from_storage() as client:
                await client.notebooks.delete(user_notebook.notebook_id)

            await db.delete_user_notebook(user_key)

            logger.info("Deleted notebook", user_key=user_key)
            return True

        except Exception as e:
            logger.error("Failed to delete notebook", error=str(e), user_key=user_key)
            return False

    # =========================================================================
    # LearnByTesting.ai Dedicated Notebook Methods
    # =========================================================================

    async def lbt_get_notebook_info(self) -> dict:
        """Get information about the LBT notebook."""
        if not NOTEBOOKLM_AVAILABLE:
            return {
                "notebook_id": settings.lbt_notebook_id,
                "notebook_name": settings.lbt_notebook_name,
                "source_count": 0,
                "is_available": False,
                "message": "NotebookLM library not available"
            }

        try:
            async with await NotebookLMClient.from_storage() as client:
                # Get the specific notebook
                notebook = await client.notebooks.get(settings.lbt_notebook_id)

                # Try to get sources count
                sources = []
                try:
                    sources = await client.sources.list(settings.lbt_notebook_id)
                except Exception:
                    pass

                return {
                    "notebook_id": settings.lbt_notebook_id,
                    "notebook_name": notebook.title if hasattr(notebook, 'title') else settings.lbt_notebook_name,
                    "source_count": len(sources),
                    "is_available": True,
                    "message": "LBT notebook is available"
                }

        except Exception as e:
            logger.error("Failed to get LBT notebook info", error=str(e))
            return {
                "notebook_id": settings.lbt_notebook_id,
                "notebook_name": settings.lbt_notebook_name,
                "source_count": 0,
                "is_available": False,
                "message": f"Error accessing notebook: {str(e)}"
            }

    async def lbt_add_source(
        self,
        source_type: SourceType,
        content: str,
        title: Optional[str] = None
    ) -> dict:
        """Add a source to the LBT notebook."""
        if not NOTEBOOKLM_AVAILABLE:
            return {"success": False, "message": "NotebookLM not available"}

        try:
            async with await NotebookLMClient.from_storage() as client:
                notebook_id = settings.lbt_notebook_id

                # Add source based on type
                if source_type == SourceType.URL:
                    await client.sources.add_url(notebook_id, url=content)
                elif source_type == SourceType.TEXT:
                    await client.sources.add_text(
                        notebook_id,
                        title=title or "LBT Context",
                        content=content
                    )
                elif source_type == SourceType.YOUTUBE:
                    await client.sources.add_url(notebook_id, url=content)
                else:
                    return {"success": False, "message": f"Unsupported source type: {source_type}"}

                logger.info("Added source to LBT notebook", source_type=source_type, title=title)
                return {
                    "success": True,
                    "message": "Source added to LBT notebook",
                    "notebook_id": notebook_id
                }

        except Exception as e:
            logger.error("Failed to add source to LBT notebook", error=str(e))
            return {"success": False, "message": f"Failed to add source: {str(e)}"}

    async def lbt_list_sources(self) -> dict:
        """List all sources in the LBT notebook."""
        if not NOTEBOOKLM_AVAILABLE:
            return {
                "notebook_id": settings.lbt_notebook_id,
                "sources": [],
                "count": 0
            }

        try:
            async with await NotebookLMClient.from_storage() as client:
                sources = await client.sources.list(settings.lbt_notebook_id)

                source_list = []
                for s in sources:
                    source_list.append({
                        "id": s.id if hasattr(s, 'id') else None,
                        "title": s.title if hasattr(s, 'title') else "Untitled",
                        "type": s.type if hasattr(s, 'type') else "unknown"
                    })

                return {
                    "notebook_id": settings.lbt_notebook_id,
                    "sources": source_list,
                    "count": len(source_list)
                }

        except Exception as e:
            logger.error("Failed to list LBT sources", error=str(e))
            return {
                "notebook_id": settings.lbt_notebook_id,
                "sources": [],
                "count": 0
            }

    async def lbt_ask(
        self,
        question: str,
        conversation_id: Optional[str] = None
    ) -> Optional[dict]:
        """Ask a question to the LBT notebook (RAG inference)."""
        if not NOTEBOOKLM_AVAILABLE:
            logger.error("NotebookLM not available")
            return None

        try:
            async with await NotebookLMClient.from_storage() as client:
                # Query the LBT notebook
                response = await client.chat.ask(
                    notebook_id=settings.lbt_notebook_id,
                    question=question
                )

                return {
                    "answer": response.answer if hasattr(response, 'answer') else str(response),
                    "sources_used": [],
                    "conversation_id": response.conversation_id if hasattr(response, 'conversation_id') else conversation_id,
                    "notebook_id": settings.lbt_notebook_id
                }

        except Exception as e:
            import traceback
            logger.error(
                "Failed to ask LBT question",
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc()
            )
            return None

    async def lbt_delete_source(self, source_id: str) -> dict:
        """Delete a source from the LBT notebook."""
        if not NOTEBOOKLM_AVAILABLE:
            return {"success": False, "message": "NotebookLM not available"}

        try:
            async with await NotebookLMClient.from_storage() as client:
                await client.sources.delete(settings.lbt_notebook_id, source_id)

                logger.info("Deleted source from LBT notebook", source_id=source_id)
                return {
                    "success": True,
                    "message": f"Source {source_id} deleted from LBT notebook"
                }

        except Exception as e:
            logger.error("Failed to delete LBT source", error=str(e), source_id=source_id)
            return {"success": False, "message": f"Failed to delete source: {str(e)}"}


# Global service instance
notebooklm_service = NotebookLMService()
