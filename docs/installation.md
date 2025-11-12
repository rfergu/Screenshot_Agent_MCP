# Installation Guide

Complete installation instructions for Screenshot Organizer on different platforms.

## System Requirements

- **Python**: 3.11 or higher
- **RAM**: 4GB minimum, 8GB recommended (for Phi-3 Vision model)
- **Disk Space**: ~10GB (includes model downloads)
- **OS**: macOS, Linux, or Windows

## Quick Installation

### 1. Install Python

Verify Python version:
```bash
python --version  # Should be 3.11+
```

If you need to install Python:

**macOS:**
```bash
brew install python@3.11
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/)

### 2. Install Tesseract OCR

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**Windows:**
1. Download installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer
3. Add Tesseract to PATH: `C:\Program Files\Tesseract-OCR`

Verify installation:
```bash
tesseract --version
```

### 3. Clone Repository

```bash
git clone <repository-url>
cd screenshot-organizer
```

### 4. Create Virtual Environment

```bash
python -m venv .venv
```

Activate virtual environment:

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```cmd
.venv\Scripts\activate
```

### 5. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### 6. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

Required environment variables:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

Optional environment variables:
```bash
LOG_LEVEL=INFO
MCP_SERVER_PORT=3000
```

### 7. Verify Installation

```bash
# Test import
python -c "from src.utils.config import load_config; print('OK')"

# Run tests
pytest tests/test_config.py -v
```

## Platform-Specific Notes

### macOS with Apple Silicon

For best performance with Phi-3 Vision MLX:

```bash
# Install MLX-specific dependency
pip install phi-3-vision-mlx==0.1.0
```

This enables hardware-accelerated vision processing on M1/M2/M3 Macs.

### Linux

Ensure Tesseract language data is installed:
```bash
sudo apt-get install tesseract-ocr-eng  # English
```

For other languages:
```bash
sudo apt-get install tesseract-ocr-all  # All languages
```

### Windows

If you encounter path issues with Tesseract:

```python
# Add to your .env file
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

Or set in Python:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Troubleshooting Installation

### Issue: pip install fails with dependency conflicts

**Solution:**
```bash
# Clear pip cache
pip cache purge

# Install with --no-cache-dir
pip install --no-cache-dir -r requirements.txt
```

### Issue: Tesseract not found

**Solution:**
```bash
# Verify tesseract is in PATH
which tesseract  # macOS/Linux
where tesseract  # Windows

# If not found, add to PATH
export PATH="/usr/local/bin:$PATH"  # macOS/Linux
```

### Issue: Python version mismatch

**Solution:**
```bash
# Use specific Python version
python3.11 -m venv .venv
source .venv/bin/activate
python --version  # Verify correct version
```

### Issue: ImportError with src modules

**Solution:**
```bash
# Ensure package is installed in editable mode
pip install -e .

# Or add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

## Uninstallation

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf .venv

# Remove downloaded models (optional)
rm -rf ~/.cache/huggingface/hub/models--phi3-vision

# Remove session data (optional)
rm -rf ~/.screenshot_organizer/
```

## Next Steps

- [Configuration Guide](configuration.md) - Customize settings
- [Usage Examples](usage-examples.md) - Learn how to use the tool
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
