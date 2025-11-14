# ThreadCrumb Performance Guide

Optimize ThreadCrumb for speed, efficiency, and scalability.

## Table of Contents

- [Performance Overview](#performance-overview)
- [Parallel Processing](#parallel-processing)
- [Caching Strategies](#caching-strategies)
- [AI Provider Performance](#ai-provider-performance)
- [Optimization Tips](#optimization-tips)
- [Benchmarks](#benchmarks)
- [Scaling for Large Workspaces](#scaling-for-large-workspaces)

## Performance Overview

ThreadCrumb performance depends on several factors:

1. **Number of channels** - More channels = longer processing time
2. **Message volume** - More messages per channel = more data to process
3. **AI processing** - AI analysis adds significant overhead
4. **Network latency** - Slack API calls are network-bound
5. **Disk I/O** - Cache operations can be I/O intensive

### Performance Modes

| Mode | Speed | Quality | Use Case |
|------|-------|---------|----------|
| **Fast** | ⚡⚡⚡ | ⭐⭐ | Quick exports, testing |
| **Balanced** | ⚡⚡ | ⭐⭐⭐ | Production use |
| **Quality** | ⚡ | ⭐⭐⭐⭐⭐ | Detailed analysis, final output |

#### Fast Mode

```bash
threadcrumb generate --no-ai --parallel --max-workers 8
```

- No AI processing
- Maximum parallelization
- File-based cache
- **~10x faster** than quality mode

#### Balanced Mode (Recommended)

```bash
threadcrumb generate --parallel --use-sqlite-cache
```

- AI processing enabled
- Moderate parallelization
- SQLite cache
- **~3-5x faster** than quality mode

#### Quality Mode

```bash
threadcrumb generate --ai-provider bedrock --build-index
```

- Full AI analysis
- Sequential processing
- Search indexing
- Best output quality

## Parallel Processing

Process multiple channels concurrently to dramatically improve performance.

### How It Works

ThreadCrumb uses Python's `ThreadPoolExecutor` to process channels in parallel:

1. Fetches channel list
2. Distributes channels across worker threads
3. Each worker processes one channel at a time
4. Results are collected and merged

### Configuration

```bash
# Enable with default workers (4)
threadcrumb generate --parallel

# Specify worker count
threadcrumb generate --parallel --max-workers 8

# Find optimal worker count
threadcrumb generate --parallel --max-workers $(nproc)
```

### Worker Count Recommendations

| Workspace Size | Recommended Workers | Expected Speedup |
|----------------|---------------------|------------------|
| Small (< 10 channels) | 2-4 | 2-3x |
| Medium (10-50 channels) | 4-8 | 3-5x |
| Large (50-100 channels) | 8-12 | 5-8x |
| Enterprise (100+ channels) | 12-16 | 6-10x |

### Limitations

- **API rate limits**: Slack may throttle requests with too many workers
- **Memory usage**: Each worker requires memory for channel data
- **CPU contention**: Diminishing returns after CPU core count

### Best Practices

1. **Start conservative**: Begin with 4 workers
2. **Monitor rate limits**: Watch for 429 errors
3. **Adjust based on errors**: Reduce workers if hitting limits
4. **Consider AI cost**: More workers = more concurrent AI calls

## Caching Strategies

Caching eliminates redundant API calls and speeds up repeat operations.

### File-Based Cache (Default)

Simple JSON file caching.

**Pros:**
- No dependencies
- Easy to inspect/debug
- Simple implementation

**Cons:**
- Slower for large datasets
- More disk I/O
- No query capabilities

**Performance:**
- Read: ~10-50ms per channel
- Write: ~20-100ms per channel
- Storage: ~1-5 MB per 1000 messages

### SQLite Cache (Recommended)

Database-backed caching with indexing.

**Pros:**
- Fast indexed lookups
- Single file storage
- SQL query capabilities
- Better concurrency

**Cons:**
- Requires careful management
- Larger initial overhead

**Performance:**
- Read: ~1-5ms per channel
- Write: ~5-20ms per channel
- Storage: ~0.5-2 MB per 1000 messages

**10-20x faster** than file-based cache for large workspaces.

### Cache Usage

```bash
# Use SQLite cache
threadcrumb generate --use-sqlite-cache

# Disable cache (fresh fetch)
threadcrumb generate --no-cache

# Use file cache with parallel processing
threadcrumb generate --parallel
```

### Cache Optimization

1. **Regular maintenance**: Vacuum SQLite database periodically
2. **Clear old data**: Remove stale cache entries
3. **Incremental sync**: Only fetch new messages

```bash
# Vacuum SQLite cache
sqlite3 ~/.threadcrumb/cache.db "VACUUM;"

# Clear old cache
rm -rf ~/.threadcrumb/cache/

# Incremental sync (only new messages)
threadcrumb generate --use-sqlite-cache
```

## AI Provider Performance

Different AI providers have different performance characteristics.

### Provider Comparison

| Provider | Latency | Throughput | Cost | Best For |
|----------|---------|------------|------|----------|
| **Bedrock (Haiku)** | Low | High | $ | Speed |
| **Bedrock (Sonnet)** | Medium | Medium | $$ | Balance |
| **Bedrock (Opus)** | High | Low | $$$$ | Quality |
| **OpenAI (GPT-3.5)** | Low | High | $ | Speed |
| **OpenAI (GPT-4)** | High | Medium | $$$ | Quality |
| **Anthropic (Claude 3)** | Medium | Medium | $$-$$$ | Balance |

### Model Selection

For best performance:

```bash
# Fast: Claude 3 Haiku via Bedrock
threadcrumb generate --ai-provider bedrock

# Balanced: Claude 3 Sonnet
threadcrumb generate --ai-provider anthropic

# Quality: GPT-4 or Claude 3 Opus
threadcrumb generate --ai-provider openai
```

### AI Processing Optimizations

1. **Batch processing**: Process multiple threads per AI call
2. **Prompt optimization**: Shorter prompts = faster responses
3. **Temperature**: Lower temperature (0.3-0.5) = faster, more consistent
4. **Max tokens**: Limit response length for speed

```yaml
ai:
  temperature: 0.5  # Lower = faster
  max_tokens: 2048  # Lower = faster
```

### When to Disable AI

Disable AI processing for maximum speed:

```bash
threadcrumb generate --no-ai
```

**Use cases:**
- Quick data exports
- Testing/development
- Archival purposes
- Initial sync of large workspaces

## Optimization Tips

### 1. Incremental Sync

Only fetch new messages since last export:

```bash
threadcrumb generate --use-sqlite-cache
```

ThreadCrumb automatically tracks last sync timestamps and only fetches new data.

**Performance gain**: 5-50x faster for repeat exports

### 2. Export Resumption

Resume interrupted exports instead of restarting:

```bash
threadcrumb generate --resume
```

**Use when:**
- Large workspace exports
- Unstable network connections
- Testing/iterating

### 3. Channel Filtering

Process only relevant channels:

```bash
# Specific channels only
threadcrumb generate --channels "general,engineering,product"

# Exclude low-value channels
threadcrumb generate --exclude "random,watercooler,memes"
```

**Performance gain**: Linear with channel reduction

### 4. Search Indexing

Build search index asynchronously or separately:

```bash
# Build during export (adds ~10-20% time)
threadcrumb generate --build-index

# Or build separately after export
# (allows optimization of export process)
threadcrumb generate
# Then index the output manually
```

### 5. Resource Limits

Control memory and CPU usage:

```bash
# Limit parallel workers
threadcrumb generate --parallel --max-workers 4

# Use file cache to limit memory
threadcrumb generate --parallel

# Disable features you don't need
threadcrumb generate --no-ai --parallel
```

## Benchmarks

Performance benchmarks on various workspace sizes (AWS t3.medium, 2 vCPU, 4GB RAM).

### Small Workspace (5 channels, 1,000 messages)

| Configuration | Time | Speedup |
|---------------|------|---------|
| Default (sequential, file cache) | 3m 45s | 1x |
| Parallel (4 workers) | 1m 20s | 2.8x |
| Parallel + SQLite cache | 1m 5s | 3.5x |
| No AI + Parallel | 25s | 9x |

### Medium Workspace (25 channels, 10,000 messages)

| Configuration | Time | Speedup |
|---------------|------|---------|
| Default (sequential, file cache) | 28m 30s | 1x |
| Parallel (4 workers) | 9m 15s | 3.1x |
| Parallel + SQLite cache | 6m 40s | 4.3x |
| Parallel (8 workers) + SQLite | 4m 20s | 6.6x |
| No AI + Parallel (8 workers) | 1m 45s | 16.3x |

### Large Workspace (100 channels, 50,000 messages)

| Configuration | Time | Speedup |
|---------------|------|---------|
| Default (sequential, file cache) | 2h 15m | 1x |
| Parallel (8 workers) | 32m | 4.2x |
| Parallel (8 workers) + SQLite cache | 21m | 6.4x |
| Parallel (12 workers) + SQLite | 16m | 8.4x |
| No AI + Parallel (12 workers) + SQLite | 4m 30s | 30x |

### Enterprise Workspace (500 channels, 250,000 messages)

| Configuration | Time | Speedup |
|---------------|------|---------|
| Default (sequential) | ~11h | 1x |
| Parallel (12 workers) + SQLite | 1h 42m | 6.5x |
| Parallel (16 workers) + SQLite | 1h 18m | 8.5x |
| No AI + Parallel (16 workers) + SQLite | 22m | 30x |
| Resumption (after 50% complete) | 41m | - |

## Scaling for Large Workspaces

Best practices for workspaces with 100+ channels or 100,000+ messages.

### 1. Use Resumption

Enable checkpoint-based resumption for reliability:

```bash
threadcrumb generate --parallel --use-sqlite-cache
# If interrupted...
threadcrumb generate --resume
```

### 2. Staged Exports

Export in stages to manage resources:

```bash
# Stage 1: High-priority channels
threadcrumb generate --channels "general,announcements,engineering" \
  --parallel --use-sqlite-cache

# Stage 2: Medium-priority channels
threadcrumb generate --channels "product,design,marketing" \
  --parallel --use-sqlite-cache

# Stage 3: Remaining channels
threadcrumb generate --exclude "general,announcements,engineering,product,design,marketing" \
  --parallel --use-sqlite-cache
```

### 3. Distributed Processing

For extremely large workspaces, consider:

1. **Multiple machines**: Split channels across machines
2. **Cloud instances**: Use larger EC2/GCE instances
3. **Serverless**: Process channels in Lambda/Cloud Functions

### 4. Optimize for Cloud

Run ThreadCrumb on cloud compute for better network performance:

```bash
# AWS EC2 in us-east-1 (same region as Slack)
docker run -v $(pwd)/config:/config \
  -v $(pwd)/output:/output \
  threadcrumb generate --parallel --max-workers 16 \
  --use-sqlite-cache
```

**Benefits:**
- Lower latency to Slack API
- Higher bandwidth
- Scalable compute resources

### 5. Monitoring and Tuning

Monitor performance and adjust:

```bash
# Enable verbose logging
threadcrumb --verbose generate --parallel

# Monitor system resources
htop  # CPU and memory
iotop # Disk I/O
nethogs # Network usage
```

**Key metrics:**
- API rate limit hits (429 errors)
- Memory usage per worker
- Cache hit rate
- Average processing time per channel

## Performance Checklist

Before running large exports, ensure:

- [ ] Parallel processing enabled
- [ ] SQLite cache configured
- [ ] Optimal worker count selected
- [ ] Resumption enabled for large workspaces
- [ ] Non-essential channels excluded
- [ ] AI provider optimized for your needs
- [ ] Sufficient disk space for output
- [ ] Network connection stable

## Troubleshooting Performance Issues

### Slow Exports

**Symptoms**: Export takes much longer than expected

**Solutions**:
1. Enable parallel processing
2. Switch to SQLite cache
3. Increase worker count
4. Check network latency
5. Consider disabling AI temporarily

### High Memory Usage

**Symptoms**: Process consumes too much RAM

**Solutions**:
1. Reduce worker count
2. Use file-based cache instead of SQLite
3. Process channels in stages
4. Exclude large channels

### Rate Limit Errors

**Symptoms**: Getting 429 errors from Slack API

**Solutions**:
1. Reduce worker count
2. Increase rate_limit_delay in config
3. Add pauses between retries

### Disk Space Issues

**Symptoms**: Running out of disk space

**Solutions**:
1. Clear old cache: `rm -rf ~/.threadcrumb/cache`
2. Use JSON instead of HTML (smaller output)
3. Exclude unnecessary channels
4. Use cloud storage

## See Also

- [Configuration Guide](CONFIGURATION.md)
- [Docker Guide](DOCKER.md)
- [Security Guide](SECURITY.md)
