# Continuous Integration Setup Guide

This guide walks contributors through wiring the FastAPI boilerplate into a continuous integration (CI) pipeline using the [`uv`](https://docs.astral.sh/uv/) toolchain and the repository's smoke/full pytest targets.

## Prerequisites

- CI runners must support Python **3.12** or higher.
- Install the `uv` binary on the runner. Most platforms can use the one-line installer:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
  ```
- Check the project out into the workspace (e.g., `git clone` or checkout action).

## Recommended Job Outline

1. **Checkout code**
2. **Install uv** (if not cached)
3. **Sync dependencies** with dev extras
4. **Cache the `.venv/` directory** between runs (optional but speeds up builds)
5. **Run environment verification** via `./scripts/verify-dev-environment.sh` to ensure logs/health probes succeed
6. **Run smoke tests** for fast verification
7. **Run the full suite** (optional on pull requests, required before merge)

### Example GitHub Actions Job

```yaml
jobs:
  tests:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> "$GITHUB_PATH"

      - name: Sync dependencies
        run: |
          uv python install 3.12
          uv venv --python "$(uv python find 3.12)"
          source .venv/bin/activate
          uv sync --dev

      - name: Verify health checks and logs
        run: |
          source .venv/bin/activate
          ./scripts/verify-dev-environment.sh

      - name: Run smoke tests
        run: uv run pytest -m smoke --maxfail=1

      - name: Run full test suite
        run: uv run pytest
```

### Example GitLab CI Stage

```yaml
stages:
  - test

tests:
  stage: test
  image: python:3.12
  before_script:
    - pip install uv
    - uv venv --python 3.12
    - source .venv/bin/activate
    - uv sync --dev
    - ./scripts/verify-dev-environment.sh
  script:
    - uv run pytest -m smoke --maxfail=1
    - uv run pytest
  cache:
    key: "${CI_COMMIT_REF_SLUG}-uv"
    paths:
      - .venv/
      - uv.lock
```

## Tips

- Use `./scripts/run-tests.sh --smoke` locally to mirror the CI smoke target.
- Pair smoke runs with `ruff check` if you want linting in the same job.
- Cache the `.venv/` folder cautiously; bust the cache when `uv.lock` or `pyproject.toml` changes.
- For matrix builds (Python versions, databases), repeat the sync/run steps per matrix entry.

With these steps in place, contributors can reproduce CI locally and ensure every pull request executes the same `uv`-backed workflow.
