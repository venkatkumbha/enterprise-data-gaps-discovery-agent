# Create a local virtualenv, install the project, generate the three systems,
# and run the SQL-guard tests. Requires Python 3.11+ on PATH.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = @(
  "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $python) { $python = "python" }

& $python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m gap_agent.synthetic.generate
.\.venv\Scripts\python -m unittest discover -s tests -v
