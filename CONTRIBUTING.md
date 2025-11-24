# Contributing to Sibyl

Thank you for your interest in contributing to Sibyl! This document provides guidelines and information for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

### Our Pledge

We are committed to making participation in this project a harassment-free experience for everyone, regardless of level of experience, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

Examples of behavior that contributes to creating a positive environment:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

Examples of unacceptable behavior:

- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

## Getting Started

### Prerequisites

- Python 3.11 or higher
- `pyenv` for Python version management
- `uv` for dependency management (recommended) or `pip`
- Git for version control
- Docker (optional, for containerized testing)

### Setting Up Development Environment

1. **Fork and clone the repository**:

   ```bash
   git clone https://github.com/yourusername/sibyl.git
   cd sibyl
   ```

2. **Run the setup script**:

   ```bash
   ./setup.sh
   ```

   This script will:
   - Install Python 3.11.9 via pyenv
   - Create a virtual environment
   - Install all dependencies with uv
   - Set up pre-commit hooks

3. **Activate the virtual environment**:

   ```bash
   source .venv/bin/activate
   ```

4. **Configure environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Verify installation**:

   ```bash
   pytest tests/core/unit --maxfail=1
   sibyl --help
   ```

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `docs/*` - Documentation updates
- `refactor/*` - Code refactoring

### Workflow Steps

1. **Create a branch** from `main` or `develop`:

   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes** following our code style guidelines

3. **Write or update tests** for your changes

4. **Run the test suite**:

   ```bash
   pytest
   ```

5. **Run code quality checks**:

   ```bash
   # Format code (v0.1.0: auto-fix style issues)
   ruff format .

   # Lint code (v0.1.0: critical errors only)
   ruff check --fix --select=F,E9,I .

   # Or use pre-commit (recommended)
   pre-commit run --all-files
   ```

   Note: Full type checking (mypy) and comprehensive linting are disabled for v0.1.0. See the [v0.1.0 Pragmatic Approach](#️-v010-pragmatic-approach) section.

6. **Commit your changes**:

   ```bash
   git add .
   git commit -m "feat: Add new feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Adding or updating tests
   - `chore:` - Maintenance tasks

7. **Push to your fork**:

   ```bash
   git push origin feature/my-new-feature
   ```

8. **Create a pull request** on GitHub

## Code Style Guidelines

### ⚠️ v0.1.0 Pragmatic Approach

**Current State**: Sibyl v0.1.0 uses **relaxed** code quality rules to enable rapid iteration and initial release. This is intentional and temporary.

**Active Checks** (via pre-commit):
- ✅ **Ruff formatting**: Consistent code style (auto-fix)
- ✅ **Critical errors only**: Undefined names, syntax errors, import sorting
- ✅ **File hygiene**: Trailing whitespace, EOF newlines, YAML/TOML validation

**Temporarily Disabled** (until v0.2.0):
- ⏸️ Type hint requirements (ANN rules)
- ⏸️ Security checks (bandit/S rules)
- ⏸️ Complexity checks (PLR, C90 rules)
- ⏸️ Full linting suite (200+ rules)

**Why This Approach?**
- No tests written yet (no safety net for aggressive fixes)
- API not stable (avoiding premature perfection)
- Urgent v0.1.0 timeline (ship first, iterate later)
- Industry standard for initial releases

**Quality Roadmap**:
- **v0.1.x**: Current state, minimal checks
- **v0.2.0**: Re-enable type hints, security checks
- **v0.3.0**: Full linting suite, 80%+ test coverage
- **v1.0.0**: Production-ready quality standards

**Using Pre-commit** (optional but recommended):
```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Bypass if needed (use sparingly!)
git commit --no-verify
```

Pre-commit runs automatically before commits but **won't block** them (exit code 0). It provides warnings to help you write better code.

**See Also**: `pyproject.toml` has detailed comments explaining the relaxed configuration.

---

### Python Code Style

We use **Ruff** for code formatting and linting (replaces Black + isort).

#### Formatting

- **Line length**: 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings (enforced by Black)
- **Imports**: Sorted by `isort` (integrated with Ruff)

#### Type Hints

All code must include type hints:

```python
def process_document(
    doc: Document,
    config: ChunkConfig,
    provider: EmbeddingProvider
) -> list[Chunk]:
    """Process a document into chunks with embeddings.

    Args:
        doc: Document to process
        config: Chunking configuration
        provider: Embedding provider instance

    Returns:
        List of processed chunks with embeddings
    """
    # Implementation
    pass
```

#### Docstrings

Use Google-style docstrings for all public functions, classes, and modules:

```python
def calculate_similarity(
    vector_a: list[float],
    vector_b: list[float]
) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vector_a: First embedding vector
        vector_b: Second embedding vector

    Returns:
        Cosine similarity score between 0 and 1

    Raises:
        ValueError: If vectors have different dimensions
    """
    pass
```

#### Naming Conventions

- **Classes**: PascalCase (e.g., `VectorStoreProvider`)
- **Functions/methods**: snake_case (e.g., `get_embedding`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_CHUNK_SIZE`)
- **Private members**: Prefix with underscore (e.g., `_internal_method`)

### YAML Configuration Style

- **Indentation**: 2 spaces
- **Keys**: snake_case
- **Comments**: Use `#` for inline explanations
- **Structure**: Keep related configuration together

```yaml
# Example workspace configuration
name: my_workspace
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
      temperature: 0.7
```

## Testing Requirements

### Test Coverage

- Maintain **minimum 80% code coverage**
- All new features must include tests
- Bug fixes must include regression tests

### Test Categories

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_chunking_algorithm():
    """Unit test for chunking algorithm."""
    pass

@pytest.mark.integration
async def test_full_rag_pipeline():
    """Integration test for complete RAG pipeline."""
    pass
```

Available markers:
- `unit` - Unit tests (fast, isolated)
- `integration` - Integration tests (slower, multiple components)
- `e2e` - End-to-end tests (full system)
- `slow` - Long-running tests
- `security` - Security-related tests

### Running Tests

```bash
# Run all tests
pytest

# Run specific test category
pytest -m unit
pytest -m integration

# Run tests in specific file
pytest tests/core/unit/test_chunking.py

# Run with coverage report
pytest --cov=sibyl --cov-report=html

# Run tests in parallel (faster)
pytest -n auto
```

### Test Structure

Organize tests to mirror source code structure:

```
tests/
├── core/
│   ├── unit/
│   │   └── test_chunking.py
│   └── integration/
│       └── test_pipeline.py
├── techniques/
│   └── test_rag_pipeline.py
└── providers/
    └── test_vector_stores.py
```

## Documentation

### Documentation Requirements

- All new features must include documentation
- Update relevant docs when modifying existing features
- Add examples for complex functionality
- Keep documentation in sync with code

### Documentation Structure

- **README.md**: Project overview and quick start
- **docs/**: Comprehensive documentation
  - `getting-started.md`: Setup and installation
  - `architecture/`: System design
  - `api/`: API reference
  - `techniques/`: Technique catalog
  - `examples/`: Tutorials and examples

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add diagrams where helpful (Mermaid diagrams in Markdown)
- Cross-reference related documentation
- Test all code examples

## Pull Request Process

### Before Submitting

1. ✅ All tests pass
2. ✅ Code coverage meets requirements (80%+)
3. ✅ Code is formatted (Black) and linted (Ruff)
4. ✅ Type checking passes (mypy)
5. ✅ Documentation is updated
6. ✅ Commit messages follow conventional commits
7. ✅ Branch is up to date with main

### Pull Request Template

When creating a PR, include:

**Title**: Follow conventional commits format

**Description**:
- Summary of changes
- Motivation and context
- Related issues (use `Fixes #123` or `Closes #456`)

**Type of Change**:
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

**Testing**:
- Describe tests you added or updated
- Note any test coverage changes

**Checklist**:
- [ ] Code follows project style guidelines
- [ ] Self-reviewed my code
- [ ] Commented complex code sections
- [ ] Updated documentation
- [ ] Added tests with good coverage
- [ ] All tests pass locally
- [ ] No new warnings or errors

### Review Process

1. Maintainers will review your PR within 5 business days
2. Address any requested changes
3. Once approved, a maintainer will merge your PR
4. Your contribution will be included in the next release

## Issue Reporting

### Bug Reports

When reporting bugs, include:

- **Title**: Clear, descriptive summary
- **Description**: What happened vs. what you expected
- **Steps to reproduce**: Detailed steps to recreate the issue
- **Environment**:
  - Python version
  - OS and version
  - Sibyl version
  - Relevant configuration
- **Logs/Error messages**: Complete error output
- **Screenshots**: If applicable

### Feature Requests

When requesting features:

- **Title**: Concise feature description
- **Problem**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives**: Other solutions you've considered
- **Additional context**: Use cases, examples

### Security Issues

**DO NOT** create public issues for security vulnerabilities.

Email security concerns to: security@sibyl-project.org

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Development Tips

### Pre-commit Hooks

Install pre-commit hooks to catch issues early:

```bash
pre-commit install
```

This will automatically:
- Format code with Black
- Run Ruff linting
- Check for common issues

### IDE Setup

#### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- Ruff

`.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true
}
```

#### PyCharm

- Enable Black formatter: Settings → Tools → Black
- Configure Ruff: Settings → Tools → External Tools

### Debugging

Use pytest with debugger:

```bash
pytest --pdb  # Drop into debugger on failure
pytest -k test_name --pdb  # Debug specific test
```

## Questions?

- **Documentation**: Check [docs/](docs/) first
- **Discussions**: Use [GitHub Discussions](https://github.com/yourusername/sibyl/discussions)
- **Issues**: Search [existing issues](https://github.com/yourusername/sibyl/issues)
- **Chat**: Join our community chat (link TBD)

## Recognition

Contributors are recognized in:
- Release notes
- CHANGELOG.md
- GitHub contributors page

Thank you for contributing to Sibyl!
