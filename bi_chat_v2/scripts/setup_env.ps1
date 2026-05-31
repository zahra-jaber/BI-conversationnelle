<#
setup_env.ps1
Creates a virtualenv (if missing), installs pinned requirements, and applies
a compatibility patch to pkg_resources when required (for Python 3.12+ / 3.14).

Usage:
  .\scripts\setup_env.ps1        # create venv if missing and install deps
  .\scripts\setup_env.ps1 -Recreate  # delete & recreate venv then install
#>
param(
    [switch]$Recreate
)

Set-StrictMode -Version Latest
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$venvPath = Join-Path $projectRoot "venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if ($Recreate -and (Test-Path $venvPath)) {
    Write-Host "Recreating virtualenv at $venvPath..."
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtualenv at $venvPath..."
    & python -m venv $venvPath
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found in venv: $pythonExe"
    exit 1
}

Write-Host "Upgrading pip and installing requirements..."
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $projectRoot "requirements.txt")

# Apply compatibility patch to pkg_resources if needed
$pkgResPath = Join-Path $venvPath "Lib\site-packages\pkg_resources\__init__.py"
if (Test-Path $pkgResPath) {
    $content = Get-Content $pkgResPath -Raw -ErrorAction Stop
    $patched = $false

    if ($content -match 'register_finder\(pkgutil\.ImpImporter, find_on_path\)') {
        Write-Host "Patching register_finder(...) occurrence..."
        $old = 'register_finder(pkgutil.ImpImporter, find_on_path)'
        $new = @'
try {
    register_finder(pkgutil.ImpImporter, find_on_path)
} catch { }
'@
        $content = $content -replace [regex]::Escape($old), $new
        $patched = $true
    }

    if ($content -match 'register_namespace_handler\(pkgutil\.ImpImporter, file_ns_handler\)') {
        Write-Host "Patching register_namespace_handler(...) occurrence..."
        $old2 = 'register_namespace_handler(pkgutil.ImpImporter, file_ns_handler)'
        $new2 = @'
try {
    register_namespace_handler(pkgutil.ImpImporter, file_ns_handler)
} catch { }
'@
        $content = $content -replace [regex]::Escape($old2), $new2
        $patched = $true
    }

    if ($patched) {
        Write-Host "Writing patched pkg_resources back to disk..."
        Set-Content -Path $pkgResPath -Value $content -Encoding UTF8
        Write-Host "Patched pkg_resources."
    } else {
        Write-Host "No patching needed for pkg_resources."
    }
} else {
    Write-Host "pkg_resources not found at $pkgResPath - skipping patch step."
}

Write-Host "Setup complete. Start the app with: .\\scripts\\run_app.ps1"
