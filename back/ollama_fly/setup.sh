#!/bin/bash

juicefs format \
    --storage s3 \
    --bucket $AWS_ENDPOINT_URL_S3/$BUCKET_NAME \
    --access-key $AWS_ACCESS_KEY_ID \
    --secret-key $AWS_SECRET_ACCESS_KEY \
    $DATABASE_URL \
    juicefs-fly

echo "Mounting JuiceFS to /root/.ollama"
juicefs mount --prefetch=256 --buffer-size=12288 -d $DATABASE_URL /root/.ollama

export OLLAMA_HOST=0.0.0.0:11434
/bin/ollama serve &
OLLAMA_PID=$!

echo "⏳ Waiting for Ollama server to be ready..."

while ! curl -f http://localhost:11434/ >/dev/null 2>&1; do
    echo "⏳ Ollama not ready yet, waiting 2 seconds..."
    sleep 2
done

echo "Ollama server is ready!"

echo "Pulling required models..."

models=("llama3.2" "nomic-embed-text")

for model in "${models[@]}"; do
    echo "Pulling model: $model"
    if ollama pull "$model"; then
        echo "Successfully pulled $model"
    else
        echo "Failed to pull $model"
        exit 1
    fi
done

echo "All models pulled successfully!"

wait $OLLAMA_PID