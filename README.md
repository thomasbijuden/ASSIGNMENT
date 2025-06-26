# Earphones Chatbot + Web App

This project combines a Rasa-powered earphones chatbot with a Reflex frontend. It requires setting up a database, running the chatbot backend, and launching the web interface.

## Project Structure

.\
├── data/\
│ └── earphones_store.db # Database file (auto-generated)\
├── earphones_chatbot/ # Rasa chatbot core\
│ ├── actions/\
│ ├── data/\
│ ├── models/\
│ └── ...\
├── frontend/ # Reflex web interface\
│ ├── assets/\
│ ├── frontend/\
│ └── ...\
├── pyproject.toml # Project dependencies\
├── setup_database.py # Database initialization script\
└── README.md # This readme file\

## Prerequisites
- Python 3.10+ [we have used 3.10.17]
- [Rasa](https://rasa.com/docs/rasa/installation) (will be installed via `uv`)
- [Reflex](https://reflex.dev/) (will be installed via `uv`)
- [UV](https://github.com/astral-sh/uv) (install with `pip install uv`)

## Setup Instructions

### 1. Initialize Database
```bash
uv run setup_db.py
```
This creates `data/earphones_db.py` containing your database.

### 2. Install Dependencies & Setup Virtual Environment
```bash
uv venv .venv             # Create virtual environment
source .venv/bin/activate # Activate venv (Linux/macOS)
.\.venv\Scripts\activate  # Activate venv (Windows)
uv pip install -e .       # Install dependencies from pyproject.toml
```

### 3. Train Rasa Model (First-Time Setup)
```bash
cd earphones_chatbot
rasa train
cd ..
```

## Running the Application
### 1. Start Rasa Action Server
```bash
cd earphones_chatbot
rasa run actions 
```

### 2. Start Rasa API Server
```bash
rasa run --enable-api --cors "*" 
cd ..
```

### 3. Launch Reflex Frontend
```bash
cd frontend
uvx reflex run
```
## Access the Application
- Chatbot API: `http://localhost:5005`
- Web Interface: `http://localhost:3000` (opens automatically)

## Shutdown Sequence
1. `Ctrl+C` in Reflex terminal
2. `Ctrl+C` in both Rasa terminals
3. Run `deactivate` to exit virtual environment

## Environment Notes
- Database path: `data/earphones_db.py`

- Rasa configuration: `earphones_chatbot/config.yml`

- Reflex config: `frontend/pc.config.py`

- Required ports:

    - `5005` (Rasa)

    - `5055` (Rasa Actions)

    - `3000` (Reflex)

    - `8000` (Reflex backend)

## Troubleshooting
- If ports are busy: Adjust in `endpoints.yml` (Rasa) or `pc.config.py` (Reflex)

- If database isn't created: Verify write permissions for `/data`

- If CORS errors: Confirm `--cors "*"` is enabled for Rasa

- If dependencies mismatch: Run `uv clean && uv pip sync`


Key features of this documentation:
1. **Visual Structure**: Clear directory tree helps users orient themselves
2. **Prerequisite Highlight**: Explicitly calls out UV requirement
3. **Concise Commands**: Uses `&` for background processes where appropriate
4. **Port Mapping**: Clearly lists required ports
5. **Troubleshooting**: Covers common setup issues
6. **Platform Agnostic**: Includes both Unix and Windows venv activation
7. **Lifecycle Management**: Includes clean shutdown instructions

For best results:
1. Place this in your repo root as `README.md`
2. Ensure all paths in your code match the structure shown
3. Add a `.gitignore` with:
- .venv/
- pycache/
- models/
- .env

