# Multi-stage build for optimized Python application
FROM python:3.13-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to a virtual environment
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim AS runtime

# Set working directory
WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/
COPY main.py ./

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app \
    && chown -R app:app /app
USER app

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose the application port
EXPOSE 8000

# Set application port to match exposed port
ENV IBKR_APPLICATION_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["python", "main.py"]
