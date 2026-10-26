# Compile image
FROM ubuntu:noble@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517 AS compile-image

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# uv provides Python 3.14 (standalone) and resolves dependencies from uv.lock.
# Pinned for reproducible builds.
COPY --from=ghcr.io/astral-sh/uv:0.11.18@sha256:78bc42400d77b0678ba95765305c826652ed5431f399257271dda681d0318f03 /uv /usr/local/bin/uv

RUN apt-get update && \
    apt-get install -y --no-install-recommends pkg-config libhdf5-dev build-essential gcc gfortran && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PROJECT_ENVIRONMENT=/app/venv

# Install the locked production dependencies plus PyInstaller (build group),
# excluding the dev group. All versions come from uv.lock.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --group build

COPY uptonight uptonight
COPY targets targets
COPY skyfield-data skyfield-data
COPY main.py .

RUN /app/venv/bin/pyinstaller --recursive-copy-metadata matplotlib --collect-all dateutil --onefile main.py

# Run image
FROM ubuntu:noble@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517 AS runtime-image

WORKDIR /app

# Copy only the necessary files from the build stage
COPY --from=compile-image /app/dist/main /app/main
COPY --from=compile-image /app/targets /app/targets
COPY --from=compile-image /app/skyfield-data /app/skyfield-data

# Run the UpTonight executable
ENTRYPOINT ["/app/main"]
