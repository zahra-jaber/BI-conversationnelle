<#
run_app.ps1
Start the Streamlit app using the project's virtualenv python executable.

Usage:
  .\scripts\run_app.ps1
#>
Set-StrictMode -Version Latest
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found in venv: $pythonExe. Run .\scripts\setup_env.ps1 first."
    exit 1
}

Write-Host "Starting Streamlit app..."
& $pythonExe -m streamlit run (Join-Path $projectRoot "app.py")
