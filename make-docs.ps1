$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$DocsPath    = Join-Path $ProjectPath "docs"
$BuildPath   = Join-Path $DocsPath "_build"
$VenvPath    = Join-Path $ProjectPath ".venv"
$PythonExe   = Join-Path $VenvPath "Scripts\python.exe"

$Languages = @("en", "ru", "de")

Write-Host "AT-CAD documentation build (EN / RU / DE)" -ForegroundColor Cyan

# ------------------------------------------------------------
# Ensure venv
# ------------------------------------------------------------
if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating virtual environment..."
    python -m venv $VenvPath
}

# ------------------------------------------------------------
# Install dependencies
# ------------------------------------------------------------
Write-Host "Installing dependencies..."
& $PythonExe -m pip install --quiet --upgrade `
    sphinx `
    sphinx-rtd-theme `
    sphinx-intl

# ------------------------------------------------------------
# Build gettext templates
# ------------------------------------------------------------
Set-Location $DocsPath
Write-Host "Generating gettext templates..."
& $PythonExe -m sphinx -b gettext . $BuildPath/gettext

# ------------------------------------------------------------
# Update / init translations
# ------------------------------------------------------------
Write-Host "Updating translations..."
& $PythonExe -m sphinx_intl update -p $BuildPath/gettext -l ru -l de

# ------------------------------------------------------------
# Build HTML for each language
# ------------------------------------------------------------
foreach ($lang in $Languages) {

    if ($lang -eq "en") {
        $OutDir = Join-Path $BuildPath "html"
        Write-Host "Building HTML (EN)..."
        & $PythonExe -m sphinx -b html . $OutDir
    }
    else {
        $OutDir = Join-Path $BuildPath "html\$lang"
        Write-Host "Building HTML ($lang)..."
        & $PythonExe -m sphinx -b html -D language=$lang . $OutDir
    }
}

# ------------------------------------------------------------
# Open result
# ------------------------------------------------------------
$IndexFile = Join-Path $BuildPath "html\index.html"
if (Test-Path $IndexFile) {
    Write-Host "Documentation built successfully." -ForegroundColor Green
    Start-Process $IndexFile
} else {
    Write-Host "ERROR: Documentation was not generated." -ForegroundColor Red
}
