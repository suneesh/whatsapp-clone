# Contributing to WhatsApp Clone Python Client

Thank you for your interest in contributing to the WhatsApp Clone Python Client! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please read and adhere to our Code of Conduct.

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/whatsapp-clone.git
cd whatsapp-clone/python-client
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"
```

### 3. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/whatsapp_client --cov-report=html

# Run specific test
pytest tests/test_async.py::TestTaskManager -v
```

## Development Workflow

### Creating a Feature Branch

```bash
# Create a feature branch from main
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-fix-name
```

### Making Changes

1. **Write code** following the style guide below
2. **Add tests** for new functionality
3. **Update documentation** as needed
4. **Run tests** to ensure nothing breaks

### Code Style

We use:
- **black** for code formatting
- **ruff** for linting
- **mypy** for type checking

Format and check your code:

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/whatsapp_client
```

### Commit Messages

Follow conventional commits:

```
type(scope): subject

body

footer
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(async): add TaskManager for background task handling
fix(client): prevent task leaks on shutdown
docs(examples): add concurrent operations example
test(async): add comprehensive async integration tests
```

### Pull Request Process

1. **Update main** before starting work
2. **Write tests** for new code
3. **Ensure all tests pass**
4. **Check coverage** (aim for 80%+)
5. **Format and lint** code
6. **Create pull request** with clear description

## Testing Guidelines

### Test Structure

```python
import pytest
from whatsapp_client import AsyncClient

class TestFeatureName:
    """Test feature name."""
    
    @pytest.mark.asyncio
    async def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        
        # Act
        
        # Assert
```

### Test Requirements

- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test interactions between components
- **Edge cases**: Test error conditions and boundaries
- **Async tests**: Mark with `@pytest.mark.asyncio`

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_async.py -v

# Specific test
pytest tests/test_async.py::TestTaskManager::test_create_task -v

# With coverage
pytest tests/ --cov=src/whatsapp_client

# Parallel execution
pytest tests/ -n auto
```

## Documentation

### Code Documentation

- Add docstrings to all public functions/classes
- Use Google-style docstrings
- Include examples for complex functions

```python
async def create_task(
    self,
    coro: Coroutine,
    name: Optional[str] = None,
) -> asyncio.Task:
    """
    Create and track a background task.
    
    Args:
        coro: Coroutine to run
        name: Optional task name for debugging
        
    Returns:
        Created task object
        
    Raises:
        RuntimeError: If manager is shutting down
        
    Example:
        >>> task = await manager.create_task(my_coro(), name="worker")
        >>> result = await task
    """
```

### Updating Documentation

- Update README.md for major changes
- Add examples for new features
- Update CHANGELOG.md
- Add docstrings to code

## Issue Reporting

### Before Creating an Issue

- Check existing issues
- Test with latest version
- Provide reproducible example

### Issue Template

```markdown
## Description
Brief description of the issue

## Reproduction
Steps to reproduce:
1. ...
2. ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- Python version: 3.11
- OS: Ubuntu 22.04
- Package version: 0.1.0

## Error Message
```
Error traceback or output
```
```

## Feature Requests

### Proposal Template

```markdown
## Summary
One-line summary

## Motivation
Why this feature is needed

## Proposed Solution
How you'd like it to work

## Example Usage
```python
# Example code
```

## Alternative Approaches
Other ways to solve this
```

## Release Process

Maintainers follow this process for releases:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Merge to main branch
4. Create GitHub release with tag `v0.1.0`
5. GitHub Actions automatically builds and publishes to PyPI

## Performance Considerations

When contributing:

- Minimize blocking operations
- Use async/await throughout
- Avoid busy-waiting loops
- Profile memory usage
- Consider edge cases with large datasets

## Security

If you discover a security vulnerability:

1. **Do not** open a public issue
2. Email security@example.com with details
3. Include steps to reproduce if possible
4. Allow time for fix before public disclosure

## Community

- **Discussions**: GitHub Discussions
- **Chat**: GitHub Issues for technical discussion
- **Twitter**: Follow for updates

## Recognition

Contributors are recognized in:
- CHANGELOG.md
- GitHub contributors page
- Release notes

Thank you for contributing! 🎉

## Resources

- [Python Style Guide (PEP 8)](https://www.python.org/dev/peps/pep-0008/)
- [Async Python Guide](https://docs.python.org/3/library/asyncio.html)
- [pytest Documentation](https://docs.pytest.org/)
- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)

## Questions?

- Open a discussion: https://github.com/suneesh/whatsapp-clone/discussions
- Create an issue: https://github.com/suneesh/whatsapp-clone/issues
- Check documentation: See README and examples

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
