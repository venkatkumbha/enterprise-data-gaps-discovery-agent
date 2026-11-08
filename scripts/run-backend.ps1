# Start the FastAPI backend on http://127.0.0.1:8000
# Run scripts/bootstrap.ps1 once before this.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m uvicorn gap_agent.api.main:app --reload --host 127.0.0.1 --port 8000
