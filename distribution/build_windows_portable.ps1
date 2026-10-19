param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"
$releaseRoot = Join-Path $projectRoot "release\Annapurna-AI-Windows"
$pyInstallerWork = Join-Path $projectRoot "release\pyinstaller-work"
$pyInstallerSpec = Join-Path $projectRoot "release\pyinstaller-spec"
$zipPath = Join-Path $projectRoot "release\Annapurna-AI-Windows.zip"

if (-not (Test-Path $python)) {
    throw "Backend virtual environment is missing. Run backend setup before building the portable package."
}

Push-Location $projectRoot
try {
    npm run build
    & $python backend\scripts\build_dataset.py
    & $python backend\scripts\train_model.py

    if (-not $SkipInstall) {
        & $python -m pip install pyinstaller
    }

    Remove-Item -LiteralPath $releaseRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $pyInstallerWork -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $pyInstallerSpec -Recurse -Force -ErrorAction SilentlyContinue

    & $python -m PyInstaller --noconfirm --clean --onedir --name AnnapurnaAI `
        --distpath $releaseRoot --workpath $pyInstallerWork --specpath $pyInstallerSpec `
        --paths $backendRoot `
        --add-data "$projectRoot\dist;frontend" `
        --add-data "$backendRoot\data\crop_training_sample.csv;data" `
        --add-data "$backendRoot\models\crop_recommender.joblib;models" `
        --add-data "$backendRoot\models\crop_recommender.metrics.json;models" `
        --add-data "$backendRoot\migrations;migrations" `
        --add-data "$backendRoot\alembic.ini;." `
        --hidden-import aiosqlite `
        --hidden-import sqlalchemy.dialects.sqlite.aiosqlite `
        --collect-submodules sklearn `
        "$PSScriptRoot\portable_server.py"

    $appDirectory = Join-Path $releaseRoot "AnnapurnaAI"
    $startScript = @'
@echo off
setlocal
cd /d "%~dp0AnnapurnaAI"
start "Annapurna AI" /B "AnnapurnaAI.exe"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo Annapurna AI is running. Keep this window open while using the app.
echo Open http://127.0.0.1:5173 if the browser does not open automatically.
pause
'@
    Set-Content -LiteralPath (Join-Path $releaseRoot "START_ANNAPURNA_AI.cmd") -Value $startScript -Encoding ASCII

    $stopScript = @'
@echo off
taskkill /IM AnnapurnaAI.exe /F >nul 2>&1
echo Annapurna AI stopped.
pause
'@
    Set-Content -LiteralPath (Join-Path $releaseRoot "STOP_ANNAPURNA_AI.cmd") -Value $stopScript -Encoding ASCII

    $guide = @'
# Annapurna AI for Windows

## Start the application

1. Extract the ZIP file to any normal folder, such as Documents.
2. Open the extracted `Annapurna-AI-Windows` folder.
3. Double-click `START_ANNAPURNA_AI.cmd`.
4. Your browser should open Annapurna AI automatically. If it does not, open `http://127.0.0.1:5173`.

Keep the black launcher window open while using the app. Double-click `STOP_ANNAPURNA_AI.cmd` when you are finished.

## Optional live AI and data services

The app runs fully without any keys; features that need one say so on screen rather than showing placeholder data. To enable them, create a file named `.env` in the `Annapurna-AI-Windows` folder and add any of:

```text
GEMINI_API_KEY=your_key
OPENWEATHER_API_KEY=your_key
AGMARKNET_API_KEY=your_key
GEMINI_MODEL=gemini-3.6-flash
```

Do not share your real API keys. Your saved plans and season budgets are stored in the `data` folder beside the executable; copy that folder to move or back up your records.

## Troubleshooting

- If Windows shows a security prompt, choose More info, then Run anyway only after confirming you received the ZIP from the project owner.
- If port 5173 is already in use, close another copy of Annapurna AI and start again.
- This is a local prototype. Crop, price, and disease outputs are decision-support guidance and should be checked with a qualified agriculture expert before expensive or treatment decisions.
'@
    Set-Content -LiteralPath (Join-Path $releaseRoot "README_FOR_FRIEND.md") -Value $guide -Encoding UTF8
    Copy-Item -LiteralPath (Join-Path $projectRoot ".env.example") -Destination (Join-Path $releaseRoot ".env.example")

    if (Test-Path $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -LiteralPath $releaseRoot -DestinationPath $zipPath -Force
    Write-Host "Portable folder: $releaseRoot"
    Write-Host "Shareable ZIP: $zipPath"
}
finally {
    Pop-Location
}
