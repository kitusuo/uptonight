# Compile image
FROM ubuntu:noble AS compile-image

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# uv provides Python 3.14 (standalone) and resolves dependencies from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && \
    apt-get install -y --no-install-recommends pkg-config libhdf5-dev build-essential gcc gfortran && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PROJECT_ENVIRONMENT=/app/venv

# Install the locked production dependencies (no dev group) plus PyInstaller.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev && \
    uv pip install --python /app/venv/bin/python pyinstaller

COPY uptonight uptonight
COPY targets targets
COPY skyfield-data skyfield-data
COPY main.py .

RUN /app/venv/bin/pyinstaller --recursive-copy-metadata matplotlib --collect-all dateutil --onefile main.py

# Run image
FROM ubuntu:noble AS runtime-image

WORKDIR /app

# Copy only the necessary files from the build stage
COPY --from=compile-image /app/dist/main /app/main
COPY --from=compile-image /app/targets /app/targets
COPY --from=compile-image /app/skyfield-data /app/skyfield-data

# Run the UpTonight executable
ENTRYPOINT ["/app/main"]
