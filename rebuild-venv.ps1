# rebuild-venv.ps1
# Полностью пересоздаёт виртуальное окружение и ставит зависимости

Write-Host "=== Пересоздание виртуального окружения (.venv) ===" -ForegroundColor Cyan

# 1. Удаляем старое окружение
if (Test-Path ".venv") {
    Write-Host "Удаляю старое окружение .venv..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".venv"
}

# 2. Создаём новое окружение
Write-Host "Создаю новое окружение .venv..." -ForegroundColor Green
python -m venv .venv

# 3. Активируем
Write-Host "Активирую окружение..." -ForegroundColor Green
. ".\.venv\Scripts\Activate.ps1"

# 4. Обновляем pip
Write-Host "Обновляю pip..." -ForegroundColor Green
python -m pip install --upgrade pip

# 5. Устанавливаем зависимости
if (Test-Path "requirements.txt") {
    Write-Host "Найден requirements.txt — ставлю зависимости..." -ForegroundColor Green
    pip install -r requirements.txt
} else {
    Write-Host "requirements.txt не найден — ставлю только Sphinx и тему." -ForegroundColor Yellow
    pip install sphinx sphinx-rtd-theme
}

Write-Host "=== Готово! Виртуальное окружение пересоздано ===" -ForegroundColor Cyan
