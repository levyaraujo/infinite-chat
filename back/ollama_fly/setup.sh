#!/bin/bash

set -e  # Exit on any error

echo "🔧 Setting up Ollama with Fly.io volume..."

# Create Ollama directory on the mounted volume
OLLAMA_DATA_DIR="/var/jfsCache/ollama"
mkdir -p "$OLLAMA_DATA_DIR"

# Create symbolic link from default Ollama location to volume
if [ ! -L "/root/.ollama" ]; then
    # Remove existing directory if it exists
    rm -rf "/root/.ollama" 2>/dev/null || true
    # Create symlink to volume
    ln -sf "$OLLAMA_DATA_DIR" "/root/.ollama"
    echo "📁 Created symlink: /root/.ollama -> $OLLAMA_DATA_DIR"
else
    echo "📁 Symlink already exists: /root/.ollama -> $OLLAMA_DATA_DIR"
fi

# Ensure proper permissions
chown -R root:root "$OLLAMA_DATA_DIR" 2>/dev/null || true

# Clean up any corrupted manifests before starting
echo "🧹 Cleaning up corrupted manifests..."
if [ -d "$OLLAMA_DATA_DIR/models/manifests" ]; then
    echo "Removing corrupted manifest files..."
    rm -rf "$OLLAMA_DATA_DIR/models/manifests/*" 2>/dev/null || true
    rm -rf "$OLLAMA_DATA_DIR/models/manifests/*" 2>/dev/null || true
fi

export OLLAMA_HOST=0.0.0.0:11434

echo "🚀 Starting Ollama server..."
/bin/ollama serve &
OLLAMA_PID=$!

echo "⏳ Waiting for Ollama server to be ready..."
RETRY_COUNT=0
MAX_RETRIES=30

while ! curl -f http://localhost:11434/ >/dev/null 2>&1; do
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Ollama server failed to start after $MAX_RETRIES attempts"
        kill $OLLAMA_PID 2>/dev/null || true
        exit 1
    fi
    echo "⏳ Ollama not ready yet, waiting 2 seconds... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

echo "✅ Ollama server is ready!"

echo "📦 Checking for required models..."

models=("llama3.2" "nomic-embed-text")

model_exists_on_disk() {
    local model_name="$1"
    local model_path="$OLLAMA_DATA_DIR/models/blobs"
    
    if [ -d "$model_path" ] && [ "$(find "$model_path" -name "sha256-*" 2>/dev/null | wc -l)" -gt 0 ]; then
        if ollama list 2>/dev/null | grep -q "^${model_name}[[:space:]]"; then
            return 0
        fi
    fi
    return 1
}

for model in "${models[@]}"; do
    if model_exists_on_disk "$model"; then
        echo "✅ Model $model already exists, skipping download"
    else
        echo "📥 Pulling model: $model (not found locally)"
        PULL_RETRY=0
        MAX_PULL_RETRIES=3
        
        while [ $PULL_RETRY -lt $MAX_PULL_RETRIES ]; do
            if ollama pull "$model"; then
                echo "✅ Successfully pulled $model"
                break
            else
                PULL_RETRY=$((PULL_RETRY + 1))
                if [ $PULL_RETRY -lt $MAX_PULL_RETRIES ]; then
                    echo "⚠️ Failed to pull $model, retrying... (attempt $PULL_RETRY/$MAX_PULL_RETRIES)"
                    # Clean up any partial downloads
                    ollama rm "$model" 2>/dev/null || true
                    sleep 5
                else
                    echo "❌ Failed to pull $model after $MAX_PULL_RETRIES attempts"
                    kill $OLLAMA_PID 2>/dev/null || true
                    exit 1
                fi
            fi
        done
    fi
done

echo "🎉 All required models are available!"

# Test the models
echo "🧪 Verifying models..."
for model in "${models[@]}"; do
    if ollama list 2>/dev/null | grep -q "^${model}[[:space:]]"; then
        echo "✅ Model $model is available and ready"
        # Get model size info
        model_info=$(ollama list | grep "^${model}[[:space:]]" | head -1)
        echo "   └─ $model_info"
    else
        echo "⚠️ Model $model not found in ollama list"
    fi
done

# Show volume usage
echo "💾 Volume usage:"
df -h /var/jfsCache 2>/dev/null || echo "   Unable to check volume usage"
du -sh "$OLLAMA_DATA_DIR" 2>/dev/null || echo "   Unable to check Ollama data size"

echo "🚀 Setup complete! Ollama is ready to serve requests."

wait $OLLAMA_PID