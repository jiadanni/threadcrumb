# Docker Usage Guide

This guide covers running ThreadCrumb in Docker containers.

## Quick Start

### 1. Build the Image

```bash
docker build -t threadcrumb:latest .
```

### 2. Run a Command

```bash
# List available commands
docker run --rm threadcrumb:latest --help

# List Slack channels
docker run --rm \
  -e SLACK_ACCESS_TOKEN=your-token \
  threadcrumb:latest list-channels

# Generate wiki
docker run --rm \
  -e SLACK_ACCESS_TOKEN=your-token \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -v $(pwd)/output:/app/output \
  threadcrumb:latest generate --format html
```

## Using Docker Compose

### Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   nano .env
   ```

3. **Create config directory:**
   ```bash
   mkdir -p config output cache
   ```

### Run Commands

```bash
# List channels
docker-compose run --rm threadcrumb list-channels

# Generate Markdown wiki
docker-compose run --rm threadcrumb generate

# Generate HTML wiki
docker-compose run --rm threadcrumb generate --format html

# Export to Confluence
docker-compose run --rm threadcrumb export-confluence

# Dry run (test without creating pages)
docker-compose run --rm threadcrumb export-confluence --dry-run
```

### Scheduled Exports

Run ThreadCrumb on a schedule (daily wiki updates):

```bash
# Start the cron service
docker-compose --profile cron up -d threadcrumb-cron

# View logs
docker-compose logs -f threadcrumb-cron

# Stop
docker-compose --profile cron down
```

## Volume Mounts

The docker-compose.yml mounts three directories:

```yaml
volumes:
  - ./config:/root/.threadcrumb    # Configuration files
  - ./output:/app/output            # Generated wikis
  - ./cache:/app/.threadcrumb/cache # Message cache
```

### Persistent Configuration

Create `config/config.yaml`:

```yaml
slack:
  rate_limit_delay: 1.0
  cache_enabled: true

ai:
  model_name: anthropic.claude-3-haiku-20240307-v1:0
  temperature: 0.7

output:
  format: html
  create_index: true

confluence:
  root_page_title: "Company Slack Wiki"
  structure: by-category
  add_labels: true
```

## Advanced Usage

### Custom Docker Image

Build with specific Python version:

```bash
docker build --build-arg PYTHON_VERSION=3.10 -t threadcrumb:py310 .
```

### Run with AWS Credentials File

```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -e AWS_PROFILE=your-profile \
  -e SLACK_ACCESS_TOKEN=your-token \
  -v $(pwd)/output:/app/output \
  threadcrumb:latest generate
```

### Multi-stage Build (Smaller Image)

Create `Dockerfile.slim`:

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml README.md ./
COPY threadcrumb ./threadcrumb
RUN pip install --no-cache-dir build && python -m build

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/dist/*.whl ./
RUN pip install --no-cache-dir *.whl && rm *.whl
ENTRYPOINT ["threadcrumb"]
CMD ["--help"]
```

Build:
```bash
docker build -f Dockerfile.slim -t threadcrumb:slim .
```

### Development Container

For development with live code reloading:

```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  threadcrumb-dev:
    build: .
    volumes:
      - .:/app
      - ./output:/app/output
    environment:
      - PYTHONPATH=/app
    command: bash
```

Run:
```bash
docker-compose -f docker-compose.dev.yml run --rm threadcrumb-dev
```

## Kubernetes Deployment

### CronJob for Scheduled Exports

Create `k8s/cronjob.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: threadcrumb-export
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: threadcrumb
            image: threadcrumb:latest
            command: ["threadcrumb", "export-confluence"]
            env:
            - name: SLACK_ACCESS_TOKEN
              valueFrom:
                secretKeyRef:
                  name: threadcrumb-secrets
                  key: slack-token
            - name: CONFLUENCE_URL
              valueFrom:
                secretKeyRef:
                  name: threadcrumb-secrets
                  key: confluence-url
            - name: CONFLUENCE_API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: threadcrumb-secrets
                  key: confluence-token
            volumeMounts:
            - name: config
              mountPath: /root/.threadcrumb
          volumes:
          - name: config
            configMap:
              name: threadcrumb-config
          restartPolicy: OnFailure
```

Create secrets:
```bash
kubectl create secret generic threadcrumb-secrets \
  --from-literal=slack-token=xoxb-your-token \
  --from-literal=confluence-url=https://yourcompany.atlassian.net \
  --from-literal=confluence-token=your-api-token
```

Deploy:
```bash
kubectl apply -f k8s/cronjob.yaml
```

## GitHub Actions with Docker

`.github/workflows/export.yml`:

```yaml
name: Export to Confluence

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t threadcrumb:latest .

      - name: Export to Confluence
        env:
          SLACK_ACCESS_TOKEN: ${{ secrets.SLACK_ACCESS_TOKEN }}
          CONFLUENCE_URL: ${{ secrets.CONFLUENCE_URL }}
          CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
          CONFLUENCE_API_TOKEN: ${{ secrets.CONFLUENCE_API_TOKEN }}
          CONFLUENCE_SPACE_KEY: ${{ secrets.CONFLUENCE_SPACE_KEY }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          docker run --rm \
            -e SLACK_ACCESS_TOKEN \
            -e CONFLUENCE_URL \
            -e CONFLUENCE_USERNAME \
            -e CONFLUENCE_API_TOKEN \
            -e CONFLUENCE_SPACE_KEY \
            -e AWS_ACCESS_KEY_ID \
            -e AWS_SECRET_ACCESS_KEY \
            threadcrumb:latest export-confluence
```

## Troubleshooting

### Permission Issues

If you get permission errors with volumes:

```bash
# Fix ownership
sudo chown -R $(id -u):$(id -g) output cache config
```

### Network Issues

If Docker can't connect to Slack/Confluence:

```bash
# Check network connectivity
docker run --rm threadcrumb:latest python -c "import requests; print(requests.get('https://api.slack.com').status_code)"
```

### Memory Issues

For large workspaces, increase Docker memory:

```bash
# In docker-compose.yml
services:
  threadcrumb:
    mem_limit: 2g
    memswap_limit: 2g
```

### Debugging

Run with verbose logging:

```bash
docker-compose run --rm threadcrumb --verbose generate
```

Get shell access:

```bash
docker run --rm -it --entrypoint bash threadcrumb:latest
```

## Best Practices

1. **Use .env file** - Never commit secrets to git
2. **Pin versions** - Use specific image tags in production
3. **Health checks** - Add health checks for long-running containers
4. **Resource limits** - Set memory/CPU limits
5. **Log aggregation** - Send logs to centralized logging
6. **Secrets management** - Use Docker secrets or vault systems
7. **Image scanning** - Scan images for vulnerabilities

## Examples

### Daily Wiki Export to Confluence

```bash
# docker-compose.override.yml
version: '3.8'
services:
  threadcrumb-daily:
    extends:
      service: threadcrumb
    command: export-confluence --structure by-category
    restart: always
    environment:
      - TZ=America/New_York
    deploy:
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

### Multi-Format Export

```bash
#!/bin/bash
# export-all.sh

formats=("markdown" "html" "json" "xml")

for format in "${formats[@]}"; do
  echo "Exporting $format..."
  docker-compose run --rm threadcrumb generate \
    --format $format \
    --output /app/output/$format
done

echo "All formats exported!"
```

Make executable and run:
```bash
chmod +x export-all.sh
./export-all.sh
```
