@echo off
REM Script to run pipe-deOWUIfied.py with user input
REM Make sure Python and the script are in your PATH or adjust paths accordingly

echo === Query Processor ===
echo.

REM Get the user's query
set /p query="Please enter your query: "

REM Check if query is empty
if "%query%"=="" (
    echo Error: Query cannot be empty!
    pause
    exit /b 1
)

echo.

REM Get the output filename
set /p filename="Please enter the output filename (without .md extension): "

REM Check if filename is empty
if "%filename%"=="" (
    echo Error: Filename cannot be empty!
    pause
    exit /b 1
)

echo.

REM Display what will be executed
echo Executing command with:
echo Query: %query%
echo Output file: %filename%.md
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH!
    pause
    exit /b 1
)

REM Check if the Python script exists
if not exist "pipe-deOWUIfied.py" (
    echo Error: pipe-deOWUIfied.py not found in current directory!
    echo Please make sure the script is in the same folder as this batch file.
    pause
    exit /b 1
)

REM Execute the Python script
python pipe-deOWUIfied.py "%query%" --base-url http://localhost:11434/v1 --api-key 0000 --model "gemma3n:e2b" --embedding-model "DC1LEX/nomic-embed-text-v1.5-multimodal:latest" --output "%filename%.md"

REM Check if the command was successful
if %errorlevel% equ 0 (
    echo.
    echo ✅ Command executed successfully!
    echo Output saved to: %filename%.md
) else (
    echo.
    echo ❌ Command failed with exit code: %errorlevel%
)

echo.
pause