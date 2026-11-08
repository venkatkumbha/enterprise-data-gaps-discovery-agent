# Start the React dev server on http://127.0.0.1:5173
# The API must already be running on port 8000.

$ErrorActionPreference = "Stop"
Set-Location (Join-Path (Split-Path -Parent $PSScriptRoot) "ui")
if (-not (Test-Path "node_modules")) {
  npm install
}
npm run dev
