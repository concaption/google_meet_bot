@echo off
setlocal EnableDelayedExpansion

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Docker is not installed. Please install Docker first.
    exit /b 1
)

REM Build the Docker image
echo Building Docker image...
docker build -t google-meet-bot .

REM Parse arguments
set DEBUG_FLAG=
set RECORD_FLAG=
set DURATION=60
set ARGS=

:parse
if "%~1"=="" goto endparse
if "%~1"=="--debug" (
    set DEBUG_FLAG=--debug
    shift
    goto parse
)
if "%~1"=="--record" (
    set RECORD_FLAG=--record
    shift
    goto parse
)
if "%~1"=="--duration" (
    set DURATION=%~2
    shift
    shift
    goto parse
)
set ARGS=%ARGS% %1
shift
goto parse
:endparse

REM Check if we have enough arguments
set ARGS=!ARGS:~1!
for /f "tokens=1,*" %%a in ("!ARGS!") do (
    set URL=%%a
    set NAME=%%b
)

if "!URL!"=="" (
    echo Usage: docker-run.bat [--debug] [--record] [--duration minutes] ^<meeting_url^> "Your Name"
    exit /b 1
)

if "!NAME!"=="" (
    echo Usage: docker-run.bat [--debug] [--record] [--duration minutes] ^<meeting_url^> "Your Name"
    exit /b 1
)

echo Starting Google Meet bot in Docker container...
echo Meeting URL: !URL!
echo Display name: !NAME!
echo Duration: !DURATION! minutes

REM Run the container
docker run --rm ^
    -v "%cd%\recordings:/app/recordings" ^
    -v "%cd%\screenshots:/app/screenshots" ^
    google-meet-bot "!URL!" "!NAME!" ^
    %DEBUG_FLAG% %RECORD_FLAG% --duration %DURATION%

echo Docker container has finished execution.
