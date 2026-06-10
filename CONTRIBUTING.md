# Contributing to LucidCam

Thank you for your interest in contributing to **LucidCam**! We welcome pull requests, bug reports, and feature suggestions.

## Getting Started

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gunther-svg/lucidcam.git
   cd lucidcam
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio flake8 mypy black isort
   ```

4. **Set up pre-commit hooks (optional but recommended):**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Style

We follow these guidelines:

- **Formatting:** Use `black` for code formatting
  ```bash
  black .
  ```
- **Import sorting:** Use `isort` for import organization
  ```bash
  isort .
  ```
- **Linting:** Use `flake8` to check for errors
  ```bash
  flake8 .
  ```
- **Type checking:** Use `mypy` for static type analysis
  ```bash
  mypy . --ignore-missing-imports
  ```

## Testing

Run tests with pytest:
```bash
pytest tests/ -v --cov=. --cov-report=html
```

## Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit with clear messages:
   ```bash
   git commit -m "feat: add support for custom themes"
   ```

3. **Push to your fork** and open a Pull Request:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Ensure all checks pass** (linting, type checking, tests).

5. **Add a description** of your changes in the PR body.

## Commit Message Format

Use conventional commits:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `refactor:` for code refactoring
- `test:` for test additions/changes
- `chore:` for dependency updates and maintenance

Example:
```
feat: add preset configuration file support

- Add lucidcam.ini for user configuration
- Make presets customizable via config file
- Add config.py for centralized settings management
```

## Reporting Issues

When reporting bugs, please include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- OS and Python version
- Relevant logs from `logs/lucidcam.log`

## Questions?

Feel free to open a GitHub Discussion or reach out via Issues.

---

**Thank you for contributing to LucidCam!** 🎭
