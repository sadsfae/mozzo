# Mozzo Smoke Tests

These tests are for **local verification only** and are NOT run in CI/CD.

## Purpose

Minimal smoke tests to verify refactoring changes don't break basic functionality.
These tests verify methods don't crash, not correctness.

## Setup

Install pytest locally (in a virtual environment):

```bash
python -m venv venv
source venv/bin/activate  # or: venv/bin/activate on Linux
pip install pytest pyyaml requests
```

## Running Tests

```bash
# Run all smoke tests
pytest tests/

# Run specific test file
pytest tests/test_smoke.py

# Run with verbose output
pytest tests/ -v
```

## Notes

- Tests use mock configuration (no real Nagios server needed)
- Tests are minimal and fast
- Not integrated into GitHub Actions
- For local development verification only
