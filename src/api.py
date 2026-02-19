"""FastAPI application for NotebookLM Microservice."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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
    SaveAnalysisRequest,
    SaveAnalysisResponse,
    AnalysisHistoryResponse,
    AnalysisRecord,
    make_user_key,
    # LBT notebook models
    LBTAddSourceRequest,
    LBTAskRequest,
    LBTAskResponse,
    LBTNotebookInfoResponse,
    LBTSourceListResponse,
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


# Validation error handler to debug 422 errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = None
    try:
        body = await request.json()
    except Exception:
        try:
            body = await request.body()
            body = body.decode() if body else None
        except Exception:
            pass

    logger.error(
        "Validation error",
        path=request.url.path,
        method=request.method,
        body=body,
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body_received": str(body)[:500] if body else None}
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
        main_category=request.main_category,
        notebook_name=request.notebook_name,
        preferred_language=request.preferred_language
    )

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or retrieve notebook. Check if NotebookLM is authenticated."
        )

    return NotebookInfo(
        user_key=notebook.user_key,
        user_email=notebook.user_email,
        main_category=notebook.main_category,
        notebook_id=notebook.notebook_id,
        notebook_name=notebook.notebook_name,
        source_count=len(notebook.sources),
        created_at=notebook.created_at,
        updated_at=notebook.updated_at
    )


@app.get("/notebooks/{user_email}/{main_category}", response_model=NotebookInfo)
async def get_notebook(user_email: str, main_category: str):
    """Get notebook info for a user by email and category."""
    user_key = make_user_key(user_email, main_category)
    notebook = await db.get_user_notebook(user_key)

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No notebook found for user_key: {user_key}"
        )

    return NotebookInfo(
        user_key=notebook.user_key,
        user_email=notebook.user_email,
        main_category=notebook.main_category,
        notebook_id=notebook.notebook_id,
        notebook_name=notebook.notebook_name,
        source_count=len(notebook.sources),
        created_at=notebook.created_at,
        updated_at=notebook.updated_at
    )


@app.delete("/notebooks/{user_email}/{main_category}")
async def delete_notebook(user_email: str, main_category: str):
    """Delete a user's notebook by email and category."""
    success = await notebooklm_service.delete_notebook(user_email, main_category)
    user_key = make_user_key(user_email, main_category)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No notebook found for user_key: {user_key}"
        )

    return {"message": f"Notebook deleted for user_key: {user_key}"}


@app.get("/notebooks")
async def list_all_notebooks():
    """List all user notebooks (admin endpoint)."""
    notebooks = await db.list_all_notebooks()
    return {
        "count": len(notebooks),
        "notebooks": [
            NotebookInfo(
                user_key=n.user_key,
                user_email=n.user_email,
                main_category=n.main_category,
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
        main_category=request.main_category,
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
    logger.info(
        "add_chess_game called",
        user_email=request.user_email,
        main_category=request.main_category,
        game_title=request.game_title,
        pgn_length=len(request.pgn) if request.pgn else 0,
        pgn_preview=request.pgn[:200] if request.pgn else None,
        has_analysis=bool(request.analysis)
    )
    success = await notebooklm_service.add_chess_game(
        user_email=request.user_email,
        main_category=request.main_category,
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
        user_key = make_user_key(request.user_email, request.main_category)
        logger.info("save_note called", user_key=user_key, title=request.title)
        response = await notebooklm_service.save_note(
            user_email=request.user_email,
            main_category=request.main_category,
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
    logger.info(
        "ask_question called",
        user_email=request.user_email,
        main_category=request.main_category,
        question=request.question[:50] if request.question else None,
        preferred_language=request.preferred_language
    )
    response = await notebooklm_service.ask_question(
        user_email=request.user_email,
        main_category=request.main_category,
        question=request.question,
        preferred_language=request.preferred_language,
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
        main_category=request.main_category,
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
# Analysis History Endpoints
# ============================================================================

@app.post("/analysis-history", response_model=SaveAnalysisResponse)
async def save_analysis(request: SaveAnalysisRequest):
    """Save an analysis to user's history."""
    try:
        user_key = make_user_key(request.user_email, request.main_category)
        logger.info("save_analysis called", user_key=user_key)

        analysis = AnalysisRecord(
            question=request.question,
            answer=request.answer,
            sources_used=request.sources_used
        )

        success = await db.save_analysis(
            user_key=user_key,
            analysis=analysis
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save analysis"
            )

        return SaveAnalysisResponse(
            success=True,
            analysis_id=analysis.analysis_id,
            message="Analysis saved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("save_analysis exception", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/analysis-history/{user_email}/{main_category}", response_model=AnalysisHistoryResponse)
async def get_analysis_history(user_email: str, main_category: str, limit: int = 20, skip: int = 0):
    """Get analysis history for a user by email and category."""
    try:
        user_key = make_user_key(user_email, main_category)
        analyses, total_count = await db.get_analysis_history(
            user_key=user_key,
            limit=limit,
            skip=skip
        )

        return AnalysisHistoryResponse(
            user_key=user_key,
            user_email=user_email,
            main_category=main_category,
            analyses=analyses,
            total_count=total_count
        )
    except Exception as e:
        logger.error("get_analysis_history exception", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


# ============================================================================
# LearnByTesting.ai Dedicated Notebook Endpoints
# ============================================================================

@app.get("/lbt/info", response_model=LBTNotebookInfoResponse)
async def lbt_get_info():
    """Get information about the LBT context notebook."""
    info = await notebooklm_service.lbt_get_notebook_info()
    return LBTNotebookInfoResponse(**info)


@app.get("/lbt/sources", response_model=LBTSourceListResponse)
async def lbt_list_sources():
    """List all sources in the LBT context notebook."""
    sources = await notebooklm_service.lbt_list_sources()
    return LBTSourceListResponse(**sources)


@app.post("/lbt/sources")
async def lbt_add_source(request: LBTAddSourceRequest):
    """Add a source to the LBT context notebook."""
    result = await notebooklm_service.lbt_add_source(
        source_type=request.source_type,
        content=request.content,
        title=request.title
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to add source")
        )

    return result


@app.delete("/lbt/sources/{source_id}")
async def lbt_delete_source(source_id: str):
    """Delete a source from the LBT context notebook."""
    result = await notebooklm_service.lbt_delete_source(source_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to delete source")
        )

    return result


@app.post("/lbt/ask", response_model=LBTAskResponse)
async def lbt_ask(request: LBTAskRequest):
    """Ask a question to the LBT context notebook (RAG inference)."""
    response = await notebooklm_service.lbt_ask(
        question=request.question,
        conversation_id=request.conversation_id
    )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get answer from LBT notebook"
        )

    return LBTAskResponse(**response)


@app.post("/lbt/context")
async def lbt_get_context(request: LBTAskRequest):
    """
    Alias for /lbt/ask - Get context from the LBT notebook.
    Use this endpoint when you need contextual information about LearnByTesting.ai.
    """
    return await lbt_ask(request)


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
