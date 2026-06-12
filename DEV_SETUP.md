Developer setup

1. Create a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

2. Run tests:

```bash
pytest -q
```

3. Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

4. Run the app locally with Docker:

```bash
docker compose up --build
```

Notes:
- CI is configured in `.github/workflows/ci.yml` to run tests on push/PR.
- Formatting is configured via `pyproject.toml` and `.pre-commit-config.yaml`.
