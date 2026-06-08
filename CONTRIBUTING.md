# Contributing to Arborinth

Thank you for your interest in contributing to Arborinth! All contributions are welcome.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/arborinth.git
   cd arborinth
   ```
3. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

```bash
# Run tests
pytest -v

# Run tests with coverage
make test-cov

# Generate HTML coverage report
make coverage
```

The project aims for **>90% test coverage**.

## Code Style

This project uses:
- [Ruff](https://astral-sh.github.io/ruff/) for linting and formatting
- [mypy](https://mypy-lang.org/) for type checking
- [mdformat](https://github.com/execle/mdformat) for markdown formatting

You can run these checks with:

```bash
# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/

# Or use the Makefile
make lint
make format
```

Pre-commit hooks are configured to run these checks automatically. Install them with:

```bash
pre-commit install
```

## Submitting Changes

1. Create a feature branch:
   ```bash
   git checkout -b my-feature-branch
   ```
2. Make your changes and add tests
3. Ensure all tests pass: `pytest -v`
4. Ensure linting passes: `make lint`
5. Commit your changes with descriptive commit messages
6. Push to your fork and open a pull request

## Pull Request Guidelines

- Follow the [pull request template](.github/PULL_REQUEST_TEMPLATE.md)
- Keep pull requests focused and small
- Include tests for new functionality
- Update documentation as needed
- Ensure all CI checks pass

## Reporting Issues

Use the appropriate [issue template](.github/ISSUE_TEMPLATE/) when reporting bugs or requesting features.

## Code of Conduct

Be respectful and inclusive. Follow standard open source etiquette.
