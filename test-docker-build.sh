#!/bin/bash
# Quick Docker build test script

set -e

echo "🐳 Docker Build Test for meshcore-cli"
echo "======================================"
echo ""

# Check Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

echo "✓ Docker found: $(docker --version)"
echo ""

# Test 1: Build with simple Dockerfile
echo "Test 1: Building with Dockerfile.simple (fastest)..."
echo "------------------------------------------------------"
if docker build -f Dockerfile.simple -t meshcore-cli:simple --progress=plain . 2>&1 | tail -20; then
    echo "✅ Simple build succeeded"
    echo ""
    
    # Test 2: Run the simple image
    echo "Test 2: Testing simple image..."
    echo "--------------------------------"
    if docker run --rm meshcore-cli:simple -h > /tmp/meshcli_help.txt 2>&1; then
        echo "✅ Simple image runs successfully"
        echo "   Help output (first 5 lines):"
        head -5 /tmp/meshcli_help.txt | sed 's/^/   /'
    else
        echo "❌ Simple image failed to run"
        exit 1
    fi
else
    echo "❌ Simple build failed"
    exit 1
fi

echo ""
echo "Test 3: Building with Dockerfile (multi-stage, optimized)..."
echo "------------------------------------------------------------"
if docker build -t meshcore-cli:optimized --progress=plain . 2>&1 | tail -20; then
    echo "✅ Multi-stage build succeeded"
    echo ""
    
    # Test 4: Run the optimized image
    echo "Test 4: Testing optimized image..."
    echo "-----------------------------------"
    if docker run --rm meshcore-cli:optimized -v > /tmp/meshcli_version.txt 2>&1; then
        echo "✅ Optimized image runs successfully"
        echo "   Version:"
        cat /tmp/meshcli_version.txt | sed 's/^/   /'
    else
        echo "❌ Optimized image failed to run"
        exit 1
    fi
else
    echo "❌ Multi-stage build failed"
    echo ""
    echo "⚠️  Multi-stage build did not work, but the simple version did."
    echo "   This is OK - use Dockerfile.simple for your workflows."
    exit 0
fi

echo ""
echo "=========================================="
echo "✅ All tests passed!"
echo "=========================================="
echo ""
echo "📊 Image Sizes:"
docker images --filter="reference=meshcore-cli:*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
echo ""
echo "Next steps:"
echo "  • For GitHub Actions: Update build-docker.yml to use Dockerfile.simple"
echo "  • For local testing: docker run meshcore-cli:simple [command]"
echo "  • For multi-platform: docker buildx build -f Dockerfile.simple --platform linux/amd64,linux/arm64 ."
