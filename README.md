# NotebookLM Microservice

A microservice that integrates Google NotebookLM with the LearnByTesting platform, enabling personalized learning through RAG (Retrieval-Augmented Generation) for chess education.

## Overview

This service provides:
- **Per-user notebooks**: Each user gets their own NotebookLM notebook
- **Chess game integration**: Add PGN games with analysis as learning sources
- **RAG inference**: Ask questions about your chess games and get personalized coaching
- **Content generation**: Generate podcasts, quizzes, and flashcards from your chess content

## Architecture

```
K8s Cluster (DigitalOcean)
    │
    └── Tailscale VPN ──→ Your Local Machine (100.x.x.x:3034)
                              │
                              └── notebooklm microservice
                                      │
                                      └── Google NotebookLM API
```

This service runs **locally** (not in K8s) because it requires browser-based Google authentication. The K8s cluster connects to it via Tailscale VPN.

## Quick Start

### 1. Setup Environment

```powershell
# Windows
cd notebooklm
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Linux/macOS
cd notebooklm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Authenticate with NotebookLM (One-time)

```powershell
# Windows
.\scripts\auth-notebooklm.ps1
```

```bash
# Linux/macOS
./scripts/auth-notebooklm.sh
```

This opens a browser for Google authentication. Credentials are stored locally.

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run the Service

```powershell
# Windows
.\scripts\run-local.ps1
```

```bash
# Linux/macOS
./scripts/run-local.sh
```

Or directly:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 3034 --reload
```

## API Endpoints

### Health
- `GET /health` - Health check with authentication status

### Notebooks
- `POST /notebooks` - Create or get notebook for user
- `GET /notebooks/{user_email}` - Get user's notebook info
- `DELETE /notebooks/{user_email}` - Delete user's notebook
- `GET /notebooks` - List all notebooks (admin)

### Sources
- `POST /sources` - Add a source (URL, file, text, YouTube)
- `POST /sources/chess-game` - Add a chess game with PGN

### Inference
- `POST /ask` - Ask a question (RAG)
- `POST /inference` - Alias for /ask

### Content Generation
- `POST /generate` - Generate podcast, quiz, or flashcards

## Example Usage

### Create notebook for user
```bash
curl -X POST http://localhost:3034/notebooks \
  -H "Content-Type: application/json" \
  -d '{"user_email": "player@example.com"}'
```

### Add a chess game
```bash
curl -X POST http://localhost:3034/sources/chess-game \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "player@example.com",
    "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6",
    "game_title": "Ruy Lopez Opening",
    "analysis": "This is the Ruy Lopez, one of the oldest chess openings..."
  }'
```

### Ask a question
```bash
curl -X POST http://localhost:3034/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "player@example.com",
    "question": "What are the key ideas in the Ruy Lopez opening?"
  }'
```

## Workflow Integration

When a user plays a chess game on LearnByTesting:

1. **Check notebook**: `GET /notebooks/{user_email}`
2. **Create if needed**: `POST /notebooks`
3. **Add game**: `POST /sources/chess-game` with PGN and analysis
4. **Query**: `POST /ask` for personalized coaching

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `3034` |
| `TAILSCALE_IP` | Tailscale IP for K8s connection | - |
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DATABASE` | Database name | `notebooklm` |
| `CHESS_AI_URL` | Chess AI service URL | `http://localhost:3020` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Tailscale Setup

1. Install Tailscale on your local machine
2. Note your Tailscale IP (e.g., `100.x.x.x`)
3. Configure K8s to route to this IP for the notebooklm service
4. Update orchestrator with your Tailscale IP

## Port Assignment

- **3034**: NotebookLM microservice (local)

## Dependencies

- Python 3.10+
- notebooklm-py (unofficial Google NotebookLM wrapper)
- FastAPI + Uvicorn
- MongoDB (for user-notebook mapping)
- Playwright (for browser authentication)

## Limitations

- **Unofficial API**: notebooklm-py uses undocumented Google APIs that may change
- **Rate limits**: Google may throttle heavy usage
- **Local only**: Requires local execution due to browser authentication
- **Single user auth**: One Google account per service instance

## Development

```bash
# Install dev dependencies
pip install pytest pytest-asyncio black ruff

# Format code
black src/

# Lint
ruff check src/

# Run tests
pytest
```
