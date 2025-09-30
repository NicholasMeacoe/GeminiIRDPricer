# Multi-stage production container for Gemini IRD Pricer (Flask)
# Final image runs as non-root and contains only runtime dependencies.

# ---- Builder stage: install runtime dependencies into a staged prefix ----
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /w

# Install build tools only if needed for wheels (kept minimal for manylinux wheels)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Final stage: copy Python runtime and app code only ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000

# Create non-root user
RUN useradd -m -u 10001 appuser
WORKDIR /app

# Copy installed runtime dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Ensure runtime data dir exists (optional)
RUN mkdir -p data/curves && chown -R appuser:appuser /app

USER appuser
EXPOSE 5000

# Default command: run Flask app
CMD ["python", "app.py"]
