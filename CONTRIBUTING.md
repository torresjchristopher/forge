# Contributing to Forge

## Development Setup

```bash
git clone https://github.com/torresjchristopher/forge.git
cd forge
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest --cov=forge
```

## Code Style

We use Black for formatting:

```bash
black forge/ tests/
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Reporting Issues

Please use the GitHub Issues tracker to report bugs or suggest features.
