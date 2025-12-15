# Offer-Sherlock

AI-powered recruitment intelligence tool for monitoring tech industry salary trends and job market dynamics.

## Overview

Offer-Sherlock is designed to help job seekers and career researchers understand the compensation landscape of major tech companies by collecting, analyzing, and visualizing recruitment offer data from the internet.

## Installation

### Prerequisites
- Python 3.11+
- uv (recommended) or pip

### Setup

1. Clone the repository:
```bash
git clone git@github.com:a-green-hand-jack/Offer-Sherlock.git
cd Offer-Sherlock
```

2. Install dependencies:
```bash
# Using uv (recommended)
uv sync

# Install in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your actual API keys and configuration
```

## Project Structure

```
Offer-Sherlock/
├── src/offer_sherlock/        # Main source code
│   ├── data/                  # Data collection and processing
│   ├── models/                # Data models and analysis
│   └── utils/                 # Utility functions
├── tests/                     # Unit and integration tests
│   ├── data/                  # Test-specific data (isolated)
│   └── outputs/               # Test outputs (isolated)
├── docs/                      # Documentation
│   ├── outlines/              # Project roadmap and progress
│   ├── dev/                   # Feature development tracking
│   └── src/                   # Module documentation
├── data/                      # Project data
│   ├── raw/                   # Raw collected data
│   └── processed/             # Processed and cleaned data
├── outputs/                   # Analysis results and models
├── scripts/                   # Executable scripts
└── experiments/               # Experimental analyses
```

## Key Features

- **Web Scraping**: Collect job offer data from multiple sources
- **Data Aggregation**: Consolidate offers from different job boards
- **Analysis**: Analyze salary trends across companies and roles
- **Visualization**: Generate insights about market dynamics
- **Intelligence**: Track compensation changes over time

## Quick Start

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/offer_sherlock

# Run specific test
pytest tests/data/test_*.py -v
```

### Code Quality
```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/
```

### Data Collection
```bash
python scripts/download_data.py
```

## Development

### Adding a New Module

1. Create module in `src/offer_sherlock/<module>/`
2. Add corresponding tests in `tests/<module>/test_*.py`
3. Document in `docs/src/<module>.md`
4. Track feature in `docs/dev/features/<feature_name>.md`

### Environment Variables

See `.env.example` for available configuration options.

## Project Status

See `docs/outlines/` for:
- `project_plan.md` - Overall roadmap and objectives
- `progress.md` - Current progress and milestones
- `milestones.md` - Completed and upcoming milestones

## Development Guidelines

See `CLAUDE.md` for detailed development instructions and project conventions.

## License

[Specify License]

## Author

- jieke wu (jieke.wu@kaust.edu.sa)

## Contributing

1. Create a feature branch
2. Write tests for new code
3. Update documentation
4. Submit a pull request

---

**Note**: This project is designed for educational and research purposes to understand job market trends in the tech industry.
