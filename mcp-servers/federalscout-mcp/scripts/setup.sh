#!/bin/bash
#
# FederalScout Development Setup
#
# Sets up development environment with all dependencies
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "========================================"
echo "FederalScout Development Setup"
echo "========================================"
echo ""

# Find Python 3.10 or higher
PYTHON_CMD=""
for py_version in python3.13 python3.12 python3.11 python3.10; do
    if command -v $py_version &> /dev/null; then
        PYTHON_CMD=$py_version
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.10 or higher is required"
    echo "Please install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
fi

python_version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Using Python: $PYTHON_CMD ($python_version)"

# Verify Python version is 3.10+
py_major=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
py_minor=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')
if [ "$py_major" -lt 3 ] || ([ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]); then
    echo "ERROR: Python 3.10 or higher is required (found $python_version)"
    exit 1
fi

# Create virtual environment
if [ -d "venv" ]; then
    # Check if existing venv uses correct Python version
    venv_python_version=$(venv/bin/python --version 2>&1 | awk '{print $2}')
    venv_py_major=$(venv/bin/python -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo "0")
    venv_py_minor=$(venv/bin/python -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")

    if [ "$venv_py_major" -lt 3 ] || ([ "$venv_py_major" -eq 3 ] && [ "$venv_py_minor" -lt 10 ]); then
        echo "⚠ Existing venv uses Python $venv_python_version (need 3.10+)"
        echo "Removing old virtual environment..."
        rm -rf venv
        echo "Creating new virtual environment with $PYTHON_CMD..."
        $PYTHON_CMD -m venv venv
    else
        echo "✓ Virtual environment exists (Python $venv_python_version)"
    fi
else
    echo "Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
fi

# Activate and install
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install -q --upgrade pip

echo "Installing dependencies..."
pip install -r requirements-test.txt

echo ""
echo "Installing Playwright browsers..."
echo "  Installing WebKit (default browser)..."
python -m playwright install webkit
echo "  Installing Chromium..."
python -m playwright install chromium
echo "  Installing Firefox..."
python -m playwright install firefox

# Create directories
echo ""
echo "Creating directories..."
mkdir -p wizards logs screenshots

echo ""
echo "========================================"
echo "✓ Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Activate venv:  source venv/bin/activate"
echo "  2. Run tests:      pytest tests/test_discovery_local.py -v"
echo "  3. See README.md for more options"
echo ""
