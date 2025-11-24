# Installation Guide

Comprehensive installation instructions for Sibyl across different platforms and use cases.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Dependency Installation](#dependency-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **Python**: 3.11 or higher
- **RAM**: 4GB
- **Storage**: 2GB for installation + space for vector databases
- **OS**: Linux, macOS, or Windows (with WSL recommended)

### Recommended Requirements

- **Python**: 3.11.9 or 3.12+
- **RAM**: 8GB+ (16GB for large-scale deployments)
- **Storage**: 10GB+ SSD for better vector database performance
- **CPU**: Multi-core processor (4+ cores recommended)

### Optional Requirements

- **GPU**: For local embedding models and LLMs (CUDA-compatible)
- **Docker**: For containerized deployment
- **PostgreSQL**: For production vector storage with pgvector

## Installation Methods

### Method 1: Quick Install with Setup Script (Recommended)

The setup script automates the entire installation process:

```bash
# Clone the repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Run setup script
./setup.sh
```

This will:
1. Check for required tools (pyenv, uv)
2. Install Python 3.11.9
3. Create virtual environment
4. Install all dependencies
5. Set up pre-commit hooks
6. Verify installation

### Method 2: Manual Installation with UV

UV is a fast Python package installer:

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install with UV
uv pip install -e ".[dev,vector,monitoring,rest]"
```

### Method 3: Manual Installation with Pip

Traditional pip installation:

```bash
# Clone repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Sibyl
pip install -e ".[dev,vector,monitoring,rest]"
```

### Method 4: Docker Installation

Run Sibyl in a container:

```bash
# Clone repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl/devops

# Copy and configure environment
cp ../.env.example ../.env
# Edit .env with your API keys

# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f sibyl-server
```

## Platform-Specific Instructions

### macOS

#### Prerequisites

Install Homebrew if not already installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Install Dependencies

```bash
# Install pyenv for Python version management
brew install pyenv

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9
```

#### Install Sibyl

```bash
# Clone and install
git clone https://github.com/yourusername/sibyl.git
cd sibyl
./setup.sh
```

#### macOS-Specific Issues

If you encounter SSL certificate errors:

```bash
# Install certificates
/Applications/Python\ 3.11/Install\ Certificates.command
```

### Linux (Ubuntu/Debian)

#### Prerequisites

Update package lists:

```bash
sudo apt update
sudo apt upgrade -y
```

#### Install Dependencies

```bash
# Install build essentials
sudo apt install -y build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
  libncurses5-dev libncursesw5-dev xz-utils tk-dev \
  libffi-dev liblzma-dev python3-openssl git

# Install pyenv
curl https://pyenv.run | bash

# Add pyenv to PATH (add to ~/.bashrc or ~/.zshrc)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9
```

#### Install Sibyl

```bash
# Clone and install
git clone https://github.com/yourusername/sibyl.git
cd sibyl
./setup.sh
```

### Linux (RHEL/CentOS/Fedora)

#### Install Dependencies

```bash
# Install development tools
sudo dnf groupinstall "Development Tools" -y
sudo dnf install -y zlib-devel bzip2 bzip2-devel readline-devel \
  sqlite sqlite-devel openssl-devel xz xz-devel libffi-devel

# Install pyenv and UV (same as Ubuntu)
curl https://pyenv.run | bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Configure PATH
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9
```

### Windows (with WSL)

#### Install WSL

```powershell
# In PowerShell (as Administrator)
wsl --install -d Ubuntu-22.04
```

Restart your computer, then open Ubuntu:

#### Install in WSL

Follow the Linux (Ubuntu/Debian) instructions above from within WSL.

#### Windows Native (Not Recommended)

While possible, we recommend WSL for the best experience. If you must use native Windows:

```powershell
# Install Python 3.11 from python.org
# Download: https://www.python.org/downloads/

# Clone repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install
pip install -e ".[dev,vector,monitoring,rest]"
```

## Dependency Installation

### Core Dependencies

Installed automatically with Sibyl:

- **mcp**: Model Context Protocol SDK
- **starlette**: Async web framework
- **uvicorn**: ASGI server
- **networkx**: Graph operations
- **pydantic**: Data validation
- **scikit-learn**: ML operations

### Optional Dependencies

#### Vector Processing

```bash
pip install -e ".[vector]"
```

Installs:
- **fastembed**: Fast local embeddings
- **faiss-cpu**: Vector similarity search

For GPU support:
```bash
pip install faiss-gpu
```

#### Monitoring

```bash
pip install -e ".[monitoring]"
```

Installs:
- **prometheus-client**: Metrics
- **opentelemetry-api**: Distributed tracing
- **opentelemetry-sdk**: Tracing implementation

#### REST API

```bash
pip install -e ".[rest]"
```

Installs:
- **fastapi**: REST API framework

#### Development Tools

```bash
pip install -e ".[dev]"
```

Installs:
- **pytest**: Testing framework
- **black**: Code formatter
- **ruff**: Linter
- **mypy**: Type checker

### External Dependencies

#### Ollama (for local LLMs)

**macOS**:
```bash
brew install ollama
ollama serve
```

**Linux**:
```bash
curl https://ollama.ai/install.sh | sh
ollama serve
```

**Pull models**:
```bash
ollama pull llama2
ollama pull mistral
```

#### PostgreSQL with pgvector (for production)

**macOS**:
```bash
brew install postgresql@15
brew services start postgresql@15

# Install pgvector
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

**Linux**:
```bash
sudo apt install postgresql-15 postgresql-server-dev-15
sudo systemctl start postgresql

# Install pgvector
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required: At least one LLM provider
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Additional providers
COHERE_API_KEY=your-cohere-key
TOGETHER_API_KEY=your-together-key

# Optional: Workspace configuration
SIBYL_WORKSPACE_FILE=config/workspaces/local_docs_duckdb.yaml

# Optional: Logging
SIBYL_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
SIBYL_LOG_FORMAT=json  # json or text

# Optional: Observability
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

### Workspace Configuration

Sibyl includes 26+ pre-configured workspaces in `config/workspaces/`. Choose one based on your needs:

**For local development**:
- `local_docs_duckdb.yaml` - DuckDB vector store, local embeddings
- `local_ollama.yaml` - Fully local (Ollama + DuckDB)

**For production**:
- `prod_pgvector.yaml` - PostgreSQL with pgvector
- `prod_qdrant.yaml` - Qdrant vector database

**For cloud**:
- `cloud_openai.yaml` - OpenAI for everything
- `cloud_anthropic.yaml` - Anthropic Claude

## Verification

### Verify Installation

```bash
# Activate virtual environment
source .venv/bin/activate

# Check Sibyl version
sibyl --version

# Check Python version
python --version  # Should be 3.11+

# List available commands
sibyl --help
```

### Run Tests

```bash
# Run quick unit tests
pytest tests/core/unit --maxfail=1

# Run all unit tests
pytest -m unit

# Run with coverage
pytest --cov=sibyl --cov-report=term-missing
```

### Verify Workspace Loading

```bash
# Test loading a workspace
sibyl workspace validate config/workspaces/local_docs_duckdb.yaml
```

### Verify Providers

```bash
# Check if API keys are loaded
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('OpenAI:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')
print('Anthropic:', 'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET')
"
```

## Troubleshooting

### Common Issues

#### Issue: pyenv not found

**Error**: `pyenv: command not found`

**Solution**:
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to PATH (Linux/macOS)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
```

#### Issue: Python build fails

**Error**: `BUILD FAILED`

**Solution**: Install build dependencies

**macOS**:
```bash
brew install openssl readline sqlite3 xz zlib
```

**Linux**:
```bash
sudo apt install -y build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev
```

#### Issue: UV installation fails

**Error**: `curl: command not found`

**Solution**: Install curl first:
```bash
# Ubuntu/Debian
sudo apt install curl

# macOS (should be pre-installed)
brew install curl
```

#### Issue: Permission denied on scripts

**Error**: `Permission denied: ./setup.sh`

**Solution**:
```bash
chmod +x setup.sh
./setup.sh
```

#### Issue: Virtual environment not activating

**Error**: `.venv/bin/activate: No such file or directory`

**Solution**: Create virtual environment first:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

#### Issue: Import errors after installation

**Error**: `ModuleNotFoundError: No module named 'sibyl'`

**Solution**: Install in editable mode:
```bash
pip install -e ".[dev,vector]"
```

#### Issue: DuckDB errors on ARM Macs

**Error**: `DuckDB binary incompatible`

**Solution**: Install architecture-specific version:
```bash
pip install --force-reinstall --no-cache-dir duckdb
```

### Platform-Specific Issues

#### macOS: SSL Certificate Errors

```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

#### Linux: Missing system libraries

```bash
# Install common dependencies
sudo apt install -y libpq-dev python3-dev
```

#### Windows: Long path issues

Enable long paths in Windows:
```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

## Updating Sibyl

### Update to Latest Version

```bash
# Navigate to Sibyl directory
cd sibyl

# Pull latest changes
git pull origin main

# Update dependencies
source .venv/bin/activate
pip install -e ".[dev,vector,monitoring,rest]" --upgrade

# Run migrations (if any)
# Check CHANGELOG.md for migration instructions
```

### Update Specific Components

```bash
# Update dependencies only
pip install --upgrade -r requirements.txt

# Rebuild environment
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,vector,monitoring,rest]"
```

## Uninstallation

### Remove Sibyl

```bash
# Deactivate virtual environment
deactivate

# Remove Sibyl directory
cd ..
rm -rf sibyl

# Optional: Remove pyenv installation
rm -rf ~/.pyenv
```

### Clean Up Data

```bash
# Remove vector databases
rm -rf data/*.duckdb

# Remove state files
rm -rf .sibyl_state/

# Remove logs
rm -rf logs/
```

## Next Steps

Now that Sibyl is installed:

1. **Configure**: Set up your [workspace](workspaces/configuration.md)
2. **Tutorial**: Follow the [Quick Start](quick-start.md) guide
3. **Learn**: Read about [Core Concepts](architecture/core-concepts.md)
4. **Examples**: Try [example applications](examples/overview.md)

## Getting Help

- **Documentation**: [docs/](README.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/sibyl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/sibyl/discussions)

---

**Next**: [Getting Started](getting-started.md) | [Quick Start](quick-start.md)
