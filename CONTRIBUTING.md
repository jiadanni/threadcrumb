# Contributing to ThreadCrumb

Thank you for your interest in contributing to ThreadCrumb! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/threadcrumb.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
5. Install in development mode: `pip install -e ".[dev]"`

## Development Workflow

1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Add tests for new functionality
4. Run tests: `pytest`
5. Format code: `black threadcrumb/`
6. Check linting: `flake8 threadcrumb/`
7. Commit your changes: `git commit -am "Add new feature"`
8. Push to your fork: `git push origin feature/your-feature-name`
9. Create a Pull Request

## Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting (line length: 100)
- Add type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and modular

## Testing

- Write tests for all new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage
- Use pytest for testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=threadcrumb

# Run specific test file
pytest tests/test_slack.py
```

## Documentation

- Update README.md if adding new features
- Add docstrings to all public APIs
- Update configuration examples if needed
- Include usage examples for new functionality

## Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Include tests for new functionality
- Ensure CI passes
- Keep PRs focused on a single feature/fix

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages/stack traces

## Feature Requests

We welcome feature requests! Please:

- Check if the feature already exists
- Clearly describe the use case
- Explain why it would be useful
- Be open to discussion

## Questions?

Feel free to open an issue for questions or join discussions.

Thank you for contributing! 🎉
