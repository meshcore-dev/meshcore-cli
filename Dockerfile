# Multi-stage build for meshcore-cli
FROM python:3.10-slim as builder

WORKDIR /build

# Copy project files
COPY . .

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Build the package
RUN pip install --upgrade pip setuptools wheel hatchling && \
    python -m hatchling build

# Runtime stage
FROM python:3.10-slim

LABEL maintainer="Florent de Lamotte <florent@frizoncorrea.fr>"
LABEL description="CLI interface to MeshCore companion radios and repeaters"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libdbus-1-3 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built package from builder
COPY --from=builder /build/dist/ /tmp/dist/

# Install the built package and dependencies
RUN pip install --no-cache-dir /tmp/dist/*.tar.gz && \
    rm -rf /tmp/dist/

# Create a non-root user
RUN useradd -m -u 1000 meshcore

USER meshcore

# Set entrypoint
ENTRYPOINT ["meshcli"]
CMD ["-h"]
