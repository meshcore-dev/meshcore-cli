# Docker Build Troubleshooting Guide

## Issue: hatchling build failed

### Root Causes
1. **Missing build dependencies** - C compiler, Python dev headers not installed
2. **Package installation issues** - Dependencies not downloading or installing
3. **Disk space or cache issues** - Docker build cache corruption

### Solutions

## Solution 1: Use the Simplified Dockerfile (Recommended)

The simplified version installs directly from source without requiring hatchling build:

```bash
docker build -f Dockerfile.simple -t meshcore-cli:latest .
```

**Advantages:**
- Simpler, more reliable
- Fewer build steps = fewer failure points
- Easier to debug
- Direct pip installation from source

**Build for multi-platform:**
```bash
docker buildx build -f Dockerfile.simple --platform linux/amd64,linux/arm64 \
  -t ghcr.io/fdlamotte/meshcore-cli:latest .
```

## Solution 2: Fix the Multi-stage Dockerfile

If you prefer the optimized multi-stage approach, use the updated `Dockerfile`:

```bash
docker build -t meshcore-cli:latest .
```

**What was fixed:**
- Added `python3-dev` for compilation
- Added `python3-venv` for virtual environment
- Added `git` package (may be needed for dependencies)
- Added error diagnostics
- Better layer caching

## Solution 3: Build with Verbose Logging

To see exactly what's failing:

```bash
# For standard docker build
docker build --progress=plain -t meshcore-cli:latest .

# For buildx (with more details)
docker buildx build --progress=plain -f Dockerfile.simple \
  --platform linux/amd64 -t meshcore-cli:latest .
```

## Solution 4: Clean and Rebuild

If you've had failed builds, clean docker cache:

```bash
# Remove only dangling images
docker image prune -f

# Or completely clean docker (WARNING - removes all images/containers not in use)
docker system prune -a -f

# Then rebuild
docker build --no-cache -t meshcore-cli:latest .
```

## Solution 5: Test Build Locally First

Before using buildx, test on your local platform:

```bash
# Test with Dockerfile.simple first (fastest)
docker build -f Dockerfile.simple -t meshcore-cli:test .

# Run to verify
docker run --rm meshcore-cli:test -h

# Then test multi-stage if you want
docker build -t meshcore-cli:test2 .
```

## Solution 6: Verify Dependencies

If build still fails, verify the package can build locally:

```bash
# On your system (not in Docker)
python -m pip install hatchling
python -m hatchling build
ls -la dist/
```

If this fails locally, the issue is in the project itself, not Docker.

## Using Dockerfile.simple vs Dockerfile

### Dockerfile.simple (Recommended for CI/CD)
- **Size impact:** Slightly larger (build dependencies included)
- **Build time:** Faster (fewer stages)
- **Reliability:** Higher (fewer steps)
- **Use case:** GitHub Actions, quick local builds

### Dockerfile (Optimized multi-stage)
- **Size impact:** Smaller (build deps removed)
- **Build time:** Slower (multi-stage, more layers)
- **Reliability:** Lower (more complex)
- **Use case:** Production deployments where size matters

## For GitHub Actions

Update `.github/workflows/build-docker.yml` to use Dockerfile.simple:

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    file: ./Dockerfile.simple          # Add this line
    push: ${{ github.event_name != 'pull_request' }}
    # ... rest of configuration
```

Or update your default Dockerfile to use the simpler approach.

## Recommended Solution

1. **For local testing:** Use `Dockerfile.simple`
   ```bash
   docker build -f Dockerfile.simple -t meshcore-cli:latest .
   ```

2. **For GitHub Actions:** Keep using `Dockerfile` (updated version) or switch to `Dockerfile.simple`

3. **For production:** Choose based on your needs:
   - If image size matters: Use `Dockerfile` (multi-stage)
   - If reliability matters: Use `Dockerfile.simple`

## Quick Commands

```bash
# Test with simple dockerfile
docker build -f Dockerfile.simple -t meshcore-cli:test .
docker run --rm meshcore-cli:test -h

# If simple works, debug multi-stage version
docker build --progress=plain -t meshcore-cli:debug .

# Multi-platform build (if simple version works)
docker buildx build -f Dockerfile.simple --platform linux/amd64,linux/arm64 \
  -t meshcore-cli:latest .
```

## Next Steps

1. Try: `docker build -f Dockerfile.simple -t meshcore-cli:latest .`
2. If it works: Use `Dockerfile.simple` in GitHub Actions
3. If multi-stage fails: Troubleshoot or stick with `Dockerfile.simple`

---

**Files Available:**
- `Dockerfile` - Multi-stage optimized version (updated with fixes)
- `Dockerfile.simple` - Single-stage reliable version (recommended)

Choose the one that works best for your use case!
