#!/bin/bash

# ============================================
# AI Intelligence Digest - Setup Script
# For Linux/macOS
# ============================================

set -e  # Exit on error

echo ""
echo "============================================"
echo "  AI Intelligence Digest - Setup"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python3 is not installed.${NC}"
    echo "Please install Python 3.10+ using your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  macOS: brew install python3"
    echo "  Fedora: sudo dnf install python3"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python found"
python3 --version
echo ""

# Step 1: Create virtual environment
echo "[1/6] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "     Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "     Virtual environment created successfully."
fi
echo ""

# Step 2: Activate virtual environment
echo "[2/6] Activating virtual environment..."
source venv/bin/activate
echo "     Virtual environment activated."
echo ""

# Step 3: Upgrade pip
echo "[3/6] Upgrading pip..."
pip install --upgrade pip --quiet
echo "     pip upgraded."
echo ""

# Step 4: Install dependencies
echo "[4/6] Installing dependencies..."
pip install -e . --quiet
echo "     Dependencies installed successfully."
echo ""

# Step 5: Create data directory
echo "[5/6] Creating data directories..."
mkdir -p data
mkdir -p output
echo "     Directories created."
echo ""

# Step 6: Setup environment file
echo "[6/6] Setting up environment file..."
if [ -f ".env" ]; then
    echo "     .env file already exists, skipping..."
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "     .env file created from .env.example"
        echo ""
        echo -e "${YELLOW}[IMPORTANT]${NC} Please edit .env file and add your credentials:"
        echo "  - EMAIL_USERNAME: Your Gmail address"
        echo "  - EMAIL_PASSWORD: Your Gmail app password"
        echo "  - TELEGRAM_BOT_TOKEN: Your Telegram bot token (optional)"
        echo "  - TELEGRAM_CHAT_ID: Your Telegram chat ID (optional)"
    else
        echo -e "${YELLOW}[WARNING]${NC} .env.example not found. Please create .env manually."
    fi
fi
echo ""

# Check if Ollama is installed
echo "============================================"
echo "  Checking Ollama..."
echo "============================================"
if ! command -v ollama &> /dev/null; then
    echo ""
    echo -e "${YELLOW}[WARNING]${NC} Ollama is not installed."
    echo "Please install Ollama from https://ollama.ai/download"
    echo ""
    echo "For Linux:"
    echo "  curl -fsSL https://ollama.ai/install.sh | sh"
    echo ""
    echo "For macOS:"
    echo "  brew install ollama"
    echo ""
    echo "After installing Ollama, run:"
    echo "  ollama pull llama3.1:8b"
    echo ""
else
    echo -e "${GREEN}[OK]${NC} Ollama found"
    ollama --version
    echo ""
    echo "Pulling llama3.1:8b model (this may take a while)..."
    ollama pull llama3.1:8b || echo -e "${YELLOW}[WARNING]${NC} Failed to pull model. Make sure Ollama is running."
fi

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your credentials"
echo "  2. Review resources/config.yml for pipeline settings"
echo "  3. Make sure Ollama is running: ollama serve"
echo "  4. Run the digest: python -m cli.run"
echo ""
echo "============================================"
echo "  Web GUI (Optional)"
echo "============================================"
echo ""
echo "To use the web interface:"
echo "  1. Initialize the GUI database:"
echo "     python -m gui.run_gui init-db"
echo ""
echo "  2. Create an admin user:"
echo "     python -m gui.run_gui create-admin"
echo ""
echo "  3. Start the web server:"
echo "     python -m gui.run_gui run --port 5000"
echo ""
echo "  4. Open http://localhost:5000 in your browser"
echo ""
echo "To activate the virtual environment later:"
echo "  source venv/bin/activate"
echo ""
