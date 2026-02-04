@echo off
REM ============================================
REM AI Intelligence Digest - Setup Script
REM For Windows
REM ============================================

echo.
echo ============================================
echo   AI Intelligence Digest - Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM Step 1: Create virtual environment
echo [1/6] Creating virtual environment...
if exist "venv" (
    echo      Virtual environment already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo      Virtual environment created successfully.
)
echo.

REM Step 2: Activate virtual environment
echo [2/6] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo      Virtual environment activated.
echo.

REM Step 3: Upgrade pip
echo [3/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo      pip upgraded.
echo.

REM Step 4: Install dependencies
echo [4/6] Installing dependencies...
pip install -e . --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo      Dependencies installed successfully.
echo.

REM Step 5: Create data directory
echo [5/6] Creating data directories...
if not exist "data" mkdir data
if not exist "output" mkdir output
echo      Directories created.
echo.

REM Step 6: Setup environment file
echo [6/6] Setting up environment file...
if exist ".env" (
    echo      .env file already exists, skipping...
) else (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo      .env file created from .env.example
        echo.
        echo [IMPORTANT] Please edit .env file and add your credentials:
        echo   - EMAIL_USERNAME: Your Gmail address
        echo   - EMAIL_PASSWORD: Your Gmail app password
        echo   - TELEGRAM_BOT_TOKEN: Your Telegram bot token (optional)
        echo   - TELEGRAM_CHAT_ID: Your Telegram chat ID (optional)
    ) else (
        echo [WARNING] .env.example not found. Please create .env manually.
    )
)
echo.

REM Check if Ollama is installed
echo ============================================
echo   Checking Ollama...
echo ============================================
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] Ollama is not installed or not in PATH.
    echo Please install Ollama from https://ollama.ai/download
    echo.
    echo After installing Ollama, run:
    echo   ollama pull llama3.1:8b
    echo.
) else (
    echo [OK] Ollama found
    ollama --version
    echo.
    echo Pulling llama3.1:8b model (this may take a while)...
    ollama pull llama3.1:8b
)

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Edit .env file with your credentials
echo   2. Review resources/config.yml for pipeline settings
echo   3. Make sure Ollama is running: ollama serve
echo   4. Run the digest: python -m cli.run
echo.
echo ============================================
echo   Web GUI (Optional)
echo ============================================
echo.
echo To use the web interface:
echo   1. Initialize the GUI database:
echo      python -m gui.run_gui init-db
echo.
echo   2. Create an admin user:
echo      python -m gui.run_gui create-admin
echo.
echo   3. Start the web server:
echo      python -m gui.run_gui run --port 5000
echo.
echo   4. Open http://localhost:5000 in your browser
echo.
echo To activate the virtual environment later:
echo   venv\Scripts\activate
echo.
pause
