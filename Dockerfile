# Multi-stage build for minimal final image
FROM python:3.12-slim AS builder

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY easyscale/ ./easyscale/
COPY README.md ./

# Final stage
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 easyscale

# Set working directory
WORKDIR /app

# Copy installed packages and application from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/easyscale ./easyscale
COPY --from=builder /app/README.md ./

# Switch to non-root user
USER easyscale

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Run the application
ENTRYPOINT ["python", "-m", "easyscale"]
CMD ["--help"]
