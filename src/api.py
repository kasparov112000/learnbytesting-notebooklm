"""FastAPI application for NotebookLM Microservice."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import structlog

from . import __version__
from .config import settings
from .database import db
from .notebooklm_service import notebooklm_service
from .models import (
    HealthResponse,
    CreateNotebookRequest,
    AddSourceRequest,
    AddChessGameRequest,
    AskQuestionRequest,
    AskQuestionResponse,
    GenerateContentRequest,
    GenerateContentResponse,
    NotebookInfo,
    UserNotebook,
    SaveNoteRequest,
    SaveNoteResponse,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting NotebookLM Microservice", port=settings.port)

    await db.connect()
    await notebooklm_service.check_auth()

    if notebooklm_service.is_authenticated:
        logger.info("NotebookLM authenticated successfully")
    else:
        logger.warning("NotebookLM not authenticated - run 'notebooklm login' first")

    yield

    # Shutdown
    await db.disconnect()
    logger.info("NotebookLM Microservice shutdown complete")


app = FastAPI(
    title="NotebookLM Microservice",
    description="Microservice for integrating Google NotebookLM with LearnByTesting platform",
    version=__version__,
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:8080",
        "https://app.learnbytesting.ai",
        "https://orchestrator.learnbytesting.ai",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="notebooklm",
        version=__version__,
        notebooklm_authenticated=notebooklm_service.is_authenticated
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "notebooklm",
        "version": __version__,
        "status": "running",
        "authenticated": notebooklm_service.is_authenticated
    }


# ============================================================================
# Notebook Management Endpoints
# ============================================================================

@app.post("/notebooks", response_model=NotebookInfo)
async def create_or_get_notebook(request: CreateNotebookRequest):
    """Create a new notebook or get existing one for a user."""
    notebook = await notebooklm_service.get_or_create_notebook(
        user_email=request.user_email,
        notebook_name=request.notebook_name
    )

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or retrieve notebook. Check if NotebookLM is authenticated."
        )

    return NotebookInfo(
        user_email=notebook.user_email,
        notebook_id=notebook.notebook_id,
        notebook_name=notebook.notebook_name,
        source_count=len(notebook.sources),
        created_at=notebook.created_at,
        updated_at=notebook.updated_at
    )


@app.get("/notebooks/{user_email}", response_model=NotebookInfo)
async def get_notebook(user_email: str):
    """Get notebook info for a user."""
    notebook = await db.get_user_notebook(user_email)

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No notebook found for user: {user_email}"
        )

    return NotebookInfo(
        user_email=notebook.user_email,
        notebook_id=notebook.notebook_id,
        notebook_name=notebook.notebook_name,
        source_count=len(notebook.sources),
        created_at=notebook.created_at,
        updated_at=notebook.updated_at
    )


@app.delete("/notebooks/{user_email}")
async def delete_notebook(user_email: str):
    """Delete a user's notebook."""
    success = await notebooklm_service.delete_notebook(user_email)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No notebook found for user: {user_email}"
        )

    return {"message": f"Notebook deleted for user: {user_email}"}


@app.get("/notebooks")
async def list_all_notebooks():
    """List all user notebooks (admin endpoint)."""
    notebooks = await db.list_all_notebooks()
    return {
        "count": len(notebooks),
        "notebooks": [
            NotebookInfo(
                user_email=n.user_email,
                notebook_id=n.notebook_id,
                notebook_name=n.notebook_name,
                source_count=len(n.sources),
                created_at=n.created_at,
                updated_at=n.updated_at
            )
            for n in notebooks
        ]
    }


# ============================================================================
# Source Management Endpoints
# ============================================================================

@app.post("/sources")
async def add_source(request: AddSourceRequest):
    """Add a source to user's notebook."""
    success = await notebooklm_service.add_source(
        user_email=request.user_email,
        source_type=request.source_type,
        content=request.content,
        title=request.title
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add source. Ensure notebook exists and NotebookLM is authenticated."
        )

    return {"message": "Source added successfully"}


@app.post("/sources/chess-game")
async def add_chess_game(request: AddChessGameRequest):
    """Add a chess game to user's notebook."""
    success = await notebooklm_service.add_chess_game(
        user_email=request.user_email,
        pgn=request.pgn,
        game_title=request.game_title,
        analysis=request.analysis
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add chess game. Ensure notebook exists and NotebookLM is authenticated."
        )

    return {"message": "Chess game added successfully"}


@app.post("/save-note", response_model=SaveNoteResponse)
async def save_note(request: SaveNoteRequest):
    """Save a note to user's notebook, creating notebook if needed."""
    try:
        logger.info("save_note called", user_email=request.user_email, title=request.title)
        response = await notebooklm_service.save_note(
            user_email=request.user_email,
            content=request.content,
            title=request.title,
            notebook_name=request.notebook_name
        )
        logger.info("save_note completed", success=response.success)

        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message
            )

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("save_note exception", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


# ============================================================================
# Inference / RAG Endpoints
# ============================================================================

@app.post("/ask", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest):
    """Ask a question to user's notebook (RAG inference)."""
    response = await notebooklm_service.ask_question(
        user_email=request.user_email,
        question=request.question,
        conversation_id=request.conversation_id
    )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get answer. Ensure notebook exists and has sources."
        )

    return response


@app.post("/inference")
async def inference(request: AskQuestionRequest):
    """Alias for /ask - inference endpoint for compatibility."""
    return await ask_question(request)


# ============================================================================
# Content Generation Endpoints
# ============================================================================

@app.post("/generate", response_model=GenerateContentResponse)
async def generate_content(request: GenerateContentRequest):
    """Generate content (podcast, quiz, flashcards) from notebook."""
    response = await notebooklm_service.generate_content(
        user_email=request.user_email,
        content_type=request.content_type,
        topic=request.topic
    )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate content."
        )

    return response


# ============================================================================
# Debug Endpoints
# ============================================================================

@app.get("/debug/notebooklm-notebooks")
async def list_notebooklm_notebooks():
    """List all notebooks in NotebookLM account (debug)."""
    if not notebooklm_service.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NotebookLM not authenticated"
        )

    notebooks = await notebooklm_service.list_notebooks()
    return {"notebooks": notebooks}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )
