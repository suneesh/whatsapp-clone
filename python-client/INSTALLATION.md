# Installation Guide

This guide covers installing the WhatsApp Clone Python Client in various environments.

## Requirements

- Python 3.9 or higher
- pip (Python package manager)
- Virtual environment recommended

## Installation Methods

### 1. PyPI Installation (Recommended)

Install the latest version from PyPI:

```bash
pip install whatsapp-client
```

### 2. Version-Specific Installation

Install a specific version:

```bash
pip install whatsapp-client==0.1.0
```

### 3. Development Installation

Install from source for development:

```bash
git clone https://github.com/suneesh/whatsapp-clone.git
cd whatsapp-clone/python-client
pip install -e .
```

### 4. With Development Dependencies

Install with testing and development tools:

```bash
pip install whatsapp-client[dev]
```

Or from source:

```bash
cd whatsapp-clone/python-client
pip install -e ".[dev]"
```

## Virtual Environment Setup

### Using venv (Built-in)

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install package
pip install whatsapp-client

# Verify installation
python -c "from whatsapp_client import AsyncClient; print('Success!')"
```

### Using conda

```bash
# Create environment
conda create -n whatsapp-client python=3.11

# Activate
conda activate whatsapp-client

# Install
pip install whatsapp-client
```

### Using poetry

```bash
# Create project
poetry new my_whatsapp_project
cd my_whatsapp_project

# Add dependency
poetry add whatsapp-client

# Install
poetry install
```

### Using pipenv

```bash
# Create environment
pipenv --python 3.11

# Install package
pipenv install whatsapp-client

# Activate
pipenv shell
```

## Verification

After installation, verify everything works:

```python
# Python REPL
>>> from whatsapp_client import AsyncClient, AsyncClient
>>> print(AsyncClient.__doc__)
```

Or run the example:

```bash
# Install examples
pip install whatsapp-client[dev]

# Download examples
git clone https://github.com/suneesh/whatsapp-clone.git
cd whatsapp-clone/python-client/examples

# Run echo bot
python echo_bot.py --server http://localhost:8000 --user testbot --password secret
```

## Troubleshooting

### ImportError: No module named 'whatsapp_client'

**Solution:**
```bash
# Ensure pip installation was successful
pip install --upgrade whatsapp-client

# Verify installation
pip list | grep whatsapp

# Check Python path
python -c "import sys; print(sys.path)"
```

### Python Version Error

**Error:** `ERROR: This project requires Python 3.9 or higher`

**Solution:**
```bash
# Check Python version
python --version

# Use specific Python version
python3.11 -m pip install whatsapp-client

# Or set up virtual environment with correct version
python3.11 -m venv venv
```

### Dependency Conflicts

**Error:** `ERROR: pip's dependency resolver does not currently take into account all the packages`

**Solution:**
```bash
# Update pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Clear cache and reinstall
pip cache purge
pip install --no-cache-dir whatsapp-client
```

### macOS Issues

**Error:** `error: command 'clang' failed with exit code 1`

**Solution:**
```bash
# Install build tools
xcode-select --install

# Reinstall
pip install --upgrade whatsapp-client
```

### Windows Issues

**Error:** `Microsoft Visual C++ 14.0 or greater is required`

**Solution:**
Download and install Visual C++ Build Tools from Microsoft, or:

```bash
# Use pre-built wheels (recommended)
pip install --only-binary :all: whatsapp-client
```

## Supported Platforms

The package supports:

- **Linux**: Ubuntu 18.04+, Debian 10+, Fedora 30+, etc.
- **macOS**: 10.14 (Mojave) and later
- **Windows**: Windows 7 SP1 and later
- **WSL/WSL2**: Windows Subsystem for Linux

All major Python versions (3.9, 3.10, 3.11, 3.12)

## Platform-Specific Wheels

Pre-built wheels are available for:

- `manylinux2014_x86_64` (Linux, x86_64)
- `manylinux2014_aarch64` (Linux, ARM64)
- `macosx_10_14_x86_64` (macOS Intel)
- `macosx_11_0_arm64` (macOS Apple Silicon)
- `win_amd64` (Windows 64-bit)
- `win32` (Windows 32-bit)

## Uninstallation

To remove the package:

```bash
pip uninstall whatsapp-client
```

## Updating

To update to the latest version:

```bash
pip install --upgrade whatsapp-client
```

To update to a specific version:

```bash
pip install whatsapp-client==0.2.0
```

## Editable Install (Development)

For active development:

```bash
git clone https://github.com/suneesh/whatsapp-clone.git
cd whatsapp-clone/python-client

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/whatsapp_client
```

## Docker Installation

For containerized deployments:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install package
RUN pip install whatsapp-client

# Copy your code
COPY . .

# Run your application
CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t my-whatsapp-app .
docker run my-whatsapp-app
```

## Next Steps

After installation, check out:

1. **Quick Start**: See README.md
2. **Examples**: Check `examples/` directory
3. **API Reference**: See `docs/` directory
4. **Contributing**: See CONTRIBUTING.md

## Getting Help

- **Documentation**: https://github.com/suneesh/whatsapp-clone/tree/main/python-client/docs
- **Examples**: https://github.com/suneesh/whatsapp-clone/tree/main/python-client/examples
- **Issues**: https://github.com/suneesh/whatsapp-clone/issues
- **Discussions**: https://github.com/suneesh/whatsapp-clone/discussions

## License

This package is licensed under the MIT License.
