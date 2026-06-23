# Contributing to YouTube Toolkit

Thank you for your interest in contributing to YouTube Toolkit! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management
- FFmpeg installed on your system

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/rhythmculture/youtube-toolkit.git
cd youtube-toolkit
```

2. Install dependencies with uv:
```bash
uv sync
```

3. Run tests to verify setup:
```bash
uv run pytest tests/ -v
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_core.py -v

# Run with coverage
uv run pytest tests/ --cov=youtube_toolkit
```

### Code Style

We follow standard Python conventions:
- Use type hints for function parameters and return values
- Write docstrings for public classes and methods
- Keep functions focused and single-purpose
- Use meaningful variable names

### Making Changes

1. Create a new branch for your feature or fix:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and add tests

3. Run tests to ensure nothing is broken:
```bash
uv run pytest tests/ -v
```

4. Commit your changes with a clear message:
```bash
git commit -m "Add: brief description of change"
```

5. Push and create a pull request

## Architecture

See [CLAUDE.md](CLAUDE.md) for the architecture and layering
(`sub_apis -> services -> handlers`) and how to add features, and
[CHANGELOG.md](CHANGELOG.md) for version history. The public API is exactly the
five sub-APIs; the old flat methods were removed in v2.0 (see
[MIGRATION.md](MIGRATION.md)).

## Types of Contributions

### Bug Reports

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages if applicable

### Feature Requests

For feature requests, please describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

### Pull Requests

PRs should:
- Include tests for new functionality
- Update documentation if needed
- Follow existing code style
- Have clear, descriptive commit messages

## Testing Guidelines

- Write tests for new features and bug fixes
- Use pytest fixtures for common test data
- Mock external API calls to avoid network dependencies
- Test edge cases and error conditions

## Questions?

If you have questions about contributing, please open an issue or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
