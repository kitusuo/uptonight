# CLAUDE.md

Fork of `mawinkler/uptonight`: computes the night's best astrophotography targets, writes plots and reports, and
publishes them over MQTT. It is packaged as a Home Assistant add-on.

## Layout

- `uptonight/`: the library (sun/moon, objects, bodies, comets, plot, report, MQTT). `main.py` is the CLI entry point
  and reads env vars or `config.yaml`.
- `uptonight-addon/`: the HA add-on. `run.sh` turns add-on options into UpTonight's config. Options and schema live in
  `config.yaml`; user docs are in `DOCS.md`.
- `ci/`: smoke-test configs and a fake supervisor. `targets/` and `skyfield-data/` are bundled data.
- `publish.sh` and `.VERSION` are upstream's Docker Hub tooling. Don't use them; CI publishes this fork's image.

## Dev

- Uses uv and Python 3.14 (`.python-version`); the project isn't installable (`package = false`).
  Run `uv sync`, then `uv run pytest`.
- Change dependencies only with `uv add` / `uv lock`, never by editing `uv.lock`. The Docker image builds with
  `uv sync --frozen`.
- Use ruff with line length 120.
- Commits use prefixes: `fix:`, `test:`, `ci:`, `build:`, `docs:`, `addon:`.
- Sync with upstream through a merge commit. Never rebase the fork.

## Tests

- Coverage must stay at least 90% on `uptonight/` (`comets.py` is excluded because it needs the network).
- Tests use a real astroplan `Observer` with offline IERS tables (`tests/conftest.py`). Don't mock astropy, and don't
  hit the network in tests.
- Never globally ignore astroplan's `TargetAlwaysUpWarning`/`TargetNeverUpWarning`. `sunmoon._sun` classifies
  darkness from those warnings.
- A new add-on option touches `config.yaml` (options and schema), `run.sh`, `DOCS.md` and
  `tests/test_addon_config_generation.py`.

## CI and release

- `test.yml` runs pytest. `docker-smoke.yml` builds the image and runs scenario tiers: file output, MQTT, comets, bad
  auth, midnight sun, polar night, and the add-on image. Merge only when both are green.
- `build-push.yaml` publishes `ghcr.io/kitusuo/uptonight` (`latest`, `sha-<short>`) on every push to `main`.
- Pin GitHub Actions to a commit SHA with a version comment, and Docker base images by digest. The add-on Dockerfile
  tracks `:latest` on purpose. Dependabot updates are weekly and grouped.
- **Add-on version bump:** HA builds the add-on on top of `:latest` and only offers an update when the add-on's
  `version` changes. Any change that reaches the image (app code, `uv.lock`, `Dockerfile`) or the add-on must, in the
  same PR, bump `version` in `uptonight-addon/config.yaml` and add a user-facing entry to
  `uptonight-addon/CHANGELOG.md`. Use a patch bump for fixes and dependency updates, minor for new options or
  features.
