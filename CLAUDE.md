# Claude Code Instructions for Offer-Sherlock

## Project Overview

Offer-Sherlock is an AI-powered recruitment intelligence tool designed to monitor tech industry salary trends and job market dynamics. The project collects offer information from the internet to help identify high-paying opportunities and track compensation changes across major tech companies.

## Core Mission

- Collect recruitment offer data from multiple sources
- Analyze salary trends and compensation patterns
- Identify market opportunities for job seekers
- Track industry-wide compensation changes over time

## Development Principles

### 1. Test-Driven Development
- Every module in `src/offer_sherlock/` must have corresponding tests in `tests/`
- Tests use isolated `tests/data/` and `tests/outputs/` directories
- Run tests before committing: `pytest`
- Target code coverage: >80%

### 2. Documentation-First
- Document new features in `docs/dev/features/<feature_name>.md`
- Update module docs in `docs/src/` when changing code
- Track dependencies between modules in `docs/src/dependencies.md`
- Keep README.md up-to-date with new capabilities

### 3. Code Quality Standards
- Format code with `black` before committing
- Check with `ruff` for linting
- Use type hints for better IDE support
- Keep functions focused and well-documented

### 4. Environment Management
- All dependencies via `pyproject.toml`
- Package installed in editable mode (`uv pip install -e .`)
- Use absolute imports (e.g., `from offer_sherlock.data import ...`)
- Load configuration from `.env` using `python-dotenv`

## Project Structure Rules

### Source Code (`src/offer_sherlock/`)

**data/** - Data collection and processing
- Web scraping implementations
- Data cleaning and validation
- Database interactions
- Data loaders and converters

**models/** - Data models and analysis
- Data model definitions
- Analysis algorithms
- Statistical computations
- Machine learning models (if applicable)

**utils/** - Utility functions
- Helper functions
- Common utilities
- Logging setup
- Configuration management

### Tests (`tests/`)

**IMPORTANT**: Must mirror `src/offer_sherlock/` structure exactly

Example mapping:
- `src/offer_sherlock/data/scraper.py` → `tests/data/test_scraper.py`
- `src/offer_sherlock/models/analyzer.py` → `tests/models/test_analyzer.py`
- `src/offer_sherlock/utils/helpers.py` → `tests/utils/test_helpers.py`

Special test directories:
- `tests/data/` - Test datasets (isolated from main project data)
- `tests/outputs/` - Test outputs (cleaned between tests)
- Use fixtures from `tests/conftest.py`

### Documentation (`docs/`)

**docs/outlines/** - Project planning and roadmap
- `project_plan.md` - Overall objectives and phases
- `progress.md` - Current status and milestones
- `milestones.md` - Completed and upcoming work

**docs/dev/** - Feature development tracking
- `feature_template.md` - Template for new features
- `features/` - Individual feature documentation

**docs/src/** - Module documentation
- `dependencies.md` - Module dependency graph
- `data.md` - Data collection and processing module
- `models.md` - Analysis and models module
- `utils.md` - Utilities module

### Scripts (`scripts/`)
- `download_data.py` - Download/collect data
- `analyze.py` - Run analysis
- `report.py` - Generate reports
- Use absolute imports from installed package
- Load environment variables from `.env`

## When Adding New Features

1. **Create feature documentation**: `docs/dev/features/<feature_name>.md`
2. **Implement in src**: `src/offer_sherlock/<module>/<feature>.py`
3. **Write comprehensive tests**: `tests/<module>/test_<feature>.py`
4. **Update module documentation**: `docs/src/<module>.md`
5. **Update dependencies**: Document in `docs/src/dependencies.md`
6. **Update progress**: Mark in `docs/outlines/progress.md`

## Common Development Tasks

### Adding a New Data Source

1. Create: `src/offer_sherlock/data/sources/<source_name>.py`
   - Implement scraper/collector class
   - Handle errors gracefully
   - Use logging

2. Test: `tests/data/test_sources_<source_name>.py`
   - Mock API calls or use test fixtures
   - Test error handling
   - Use `tests/data/` for test data

3. Document: Update `docs/src/data.md`
4. Feature track: `docs/dev/features/add_<source_name>_source.md`
5. Update: `docs/src/dependencies.md` if it depends on other modules

### Adding a New Analysis

1. Create: `src/offer_sherlock/models/<analysis_name>.py`
2. Test: `tests/models/test_<analysis_name>.py`
3. Document: Update `docs/src/models.md`
4. Feature track: `docs/dev/features/<analysis_name>.md`

### Adding a New Utility

1. Create: `src/offer_sherlock/utils/<utility_name>.py`
2. Test: `tests/utils/test_<utility_name>.py`
3. Document: Update `docs/src/utils.md`

### Creating a New Script

1. Create: `scripts/<script_name>.py`
2. Use environment variables:
   ```python
   from dotenv import load_dotenv
   import os
   
   load_dotenv()
   data_dir = os.getenv('DATA_DIR')
   ```
3. Import from installed package:
   ```python
   from offer_sherlock.data import load_offers
   ```
4. Document usage in `README.md`

## Environment Variables

Always use `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()

data_dir = os.getenv('DATA_DIR')
api_key = os.getenv('OPENAI_API_KEY')
```

Reference `.env.example` for available variables.

## Testing Guidelines

- Use `pytest` for all tests
- Use fixtures in `tests/conftest.py` for common setup
- Isolated test data in `tests/data/`
- Test outputs go to `tests/outputs/`
- Aim for >80% code coverage
- Mock external API calls
- Test error cases and edge cases

Run before committing:
```bash
pytest --cov=src/offer_sherlock
```

## Code Style Guidelines

- Line length: 100 characters (black default)
- Use type hints where practical
- Use descriptive variable names
- Comments only for non-obvious logic
- Follow PEP 8 conventions

## Important Reminders

✓ Always create tests for new code
✓ Always update documentation before submitting code
✓ Use editable install (no relative imports)
✓ Keep tests isolated from main data/outputs
✓ Track feature development in docs/dev/
✓ Document module dependencies
✓ Use absolute imports from installed package
✓ Load configuration from .env, never hardcode

## Dependency Management

When adding dependencies:
1. Add to `pyproject.toml` under appropriate section
2. Run `uv sync` or `uv pip install -e ".[dev]"`
3. Update `docs/src/dependencies.md` if it affects module structure

### Dependency Groups

- **Core**: Required for basic functionality (data collection, analysis)
- **dev**: Development tools (pytest, black, ruff, mypy)
- **ml**: Machine learning dependencies (numpy, scikit-learn, torch)
- **web**: Web framework dependencies (fastapi, sqlalchemy)

## Git Workflow

1. Create feature branch: `git checkout -b feature/<feature-name>`
2. Make changes with tests
3. Update documentation
4. Run full test suite: `pytest --cov`
5. Commit with clear message
6. Push and create pull request

## Performance Considerations

- Be mindful of API rate limits when scraping
- Cache processed data appropriately
- Profile slow operations
- Consider data size impacts

## Deployment & Distribution

- Package is installable: `pip install -e .`
- Can be published to PyPI later
- Scripts should be self-contained and executable
- Document any external dependencies

## Future Roadmap

See `docs/outlines/project_plan.md` for upcoming features and phases.

---

**Last Updated**: 2025-12-15
