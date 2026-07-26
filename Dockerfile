# Multi-stage build for meshcore-cli
FROM python:3.10-slim AS builder

WORKDIR /build

# Copy project files
COPY . .

# Install comprehensive build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    python3-venv \
    git \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install build tools
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build dependencies
RUN pip install --upgrade pip setuptools wheel hatchling packaging

# Build the package with error handling
RUN python -m hatchling build 2>&1 || (echo "Build failed, checking environment:" && \
    python --version && \
    pip --version && \
    python -c "import hatchling; print('hatchling version:', hatchling.__version__)" && \
    exit 1)

# Runtime stage
FROM python:3.10-slim

LABEL maintainer="Florent de Lamotte <florent@frizoncorrea.fr>"
LABEL description="CLI interface to MeshCore companion radios and repeaters"

# Install runtime dependencies and pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    libdbus-1-3 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip for reliable package installation
RUN pip install --upgrade pip

WORKDIR /app

# Copy built package from builder
COPY --from=builder /build/dist/ /tmp/dist/

# Install the built package with error handling
RUN if [ -z "$(ls -A /tmp/dist/)" ]; then \
    echo "ERROR: No distribution files found in builder!"; \
    exit 1; \
    fi && \
    pip install --no-cache-dir /tmp/dist/*.tar.gz && \
    rm -rf /tmp/dist/

# Create a non-root user
RUN useradd -m -u 1000 meshcore

USER meshcore

# Set entrypoint
ENTRYPOINT ["meshcli"]
CMD ["-h"]
