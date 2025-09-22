# make-docs.ps1
# Полная сборка документации Sphinx для проекта AT-CAD с кастомным стилем

$ProjectPath = "E:\AT-CAD"
$DocsPath = Join-Path $ProjectPath "docs"
$BuildPath = Join-Path $DocsPath "build"
$ModulesRst = Join-Path $DocsPath "modules.rst"
$StaticPath = Join-Path $DocsPath "_static"

# --- Переходим в корень проекта ---
Set-Location $ProjectPath

# --- Проверяем и создаём папку _static ---
if (-not (Test-Path $StaticPath)) {
    Write-Host "Creating _static folder..."
    New-Item -ItemType Directory -Path $StaticPath | Out-Null
}

# --- Очистка старой сборки ---
if (Test-Path $BuildPath) {
    Write-Host "Removing old build..."
    Remove-Item -Recurse -Force $BuildPath
}

# --- Получаем все Python модули (исключая __init__.py и .venv) ---
$PythonFiles = Get-ChildItem -Recurse -File -Include *.py |
    Where-Object { $_.Name -ne "__init__.py" -and $_.FullName -notmatch "\\.venv\\" }

# --- Генерация modules.rst ---
Write-Host "Generating modules.rst..."
@"
Modules Documentation
=====================

.. toctree::
   :maxdepth: 2
"@ | Set-Content $ModulesRst -Encoding UTF8

foreach ($file in $PythonFiles) {
    $relative = $file.FullName.Substring($ProjectPath.Length + 1) -replace "\\", "."
    $moduleName = $relative -replace ".py$",""

    @(
        "",
        ".. automodule:: $moduleName",
        "    :members:",
        "    :undoc-members:",
        "    :show-inheritance:",
        ""
    ) | Add-Content -Path $ModulesRst -Encoding UTF8
}

# --- Сборка HTML документации ---
Write-Host "Building HTML documentation..."
Set-Location $DocsPath
sphinx-build -b html . $BuildPath

# --- Открываем документацию в браузере ---
Write-Host "Opening documentation in browser..."
Start-Process (Join-Path $BuildPath "index.html")

Write-Host "Documentation build completed!"

