FROM python:3.11-slim

LABEL maintainer="ThreadCrumb Team"
LABEL description="AI-powered Slack workspace analyzer and wiki generator"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY threadcrumb ./threadcrumb

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create directories for config and output
RUN mkdir -p /root/.threadcrumb /app/output

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
ENTRYPOINT ["threadcrumb"]
CMD ["--help"]
