# Contributing to Tux Wallpaper

Thank you for your interest in contributing to Tux Wallpaper!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/tux-wallpaper.git
cd tux-wallpaper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies with dev tools
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Project Structure

```
tux-wallpaper/
├── tux_wallpaper/       # Main Python package
│   ├── player/          # mpv wallpaper player engine
│   └── service/         # Local API service
├── server/              # Remote wallpaper server (FastAPI)
├── web/                  # Frontend UI (HTML/CSS/JS)
├── tests/                # Test suite
├── config/               # Configuration files
└── data/                 # Downloaded wallpapers
```

## Branching Strategy

```
main              # Stable release branch
├── develop       # Integration branch for features
└── feature/xxx  # Feature branches
```

- **main**: Always deployable, requires PR review and passing CI
- **develop**: All features merge here before release
- **feature/xxx**: Work on specific features or bug fixes

## Commit Messages

Follow the conventional commit format:

```
type: short description

Optional detailed explanation.

Closes #123
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructuring without behavior change
- `test:` Adding or updating tests
- `docs:` Documentation changes
- `chore:` Maintenance tasks

## Coding Standards

### Python

- Follow PEP 8 (enforced by ruff)
- Use type hints on all function signatures
- Maximum line length: 100 characters
- Sort imports with isort

```bash
# Format code
ruff format .
isort .

# Run linters
ruff check .

# Type checking
mypy tux_wallpaper/
```

### Testing

- Write tests **before** writing implementation code (TDD)
- All new code must have associated tests
- Core modules require >80% test coverage
- Tests must pass before merging

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tux_wallpaper --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_player.py -v
```

### Test Naming

Test names should clearly describe what they verify:

```python
# Good
def test_load_valid_file_updates_current_file(self) -> None:

# Bad
def test_load(self) -> None:
```

## Pull Request Process

1. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Write code and tests** following the standards above.

3. **Ensure tests pass**:
   ```bash
   pytest
   ruff check .
   mypy tux_wallpaper/
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new wallpaper preview feature"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Code review**: At least one approval required before merge.

## Areas Requiring Special Attention

### Modifying `player/` Module

The `player/` module contains the core wallpaper playback logic.
- Any changes must include updated tests
- Reviewer must verify behavior hasn't changed for existing functionality

### Modifying `service/api.py`

API changes affect the contract between frontend and backend:
- Document any new endpoints in API.md
- Update OpenAPI schema if applicable
- Ensure backward compatibility when possible

### Database Migrations

If changing the database schema in `service/db.py`:
- Use migrations for production (see alembic if added)
- Update schema version constant
- Write migration tests

## Reporting Issues

When reporting bugs, include:
- Python version
- Linux distribution and version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output (with `debug: true` enabled)

## Questions?

Feel free to open an issue for discussion before starting large changes.
