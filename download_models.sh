#!/bin/bash

set -e

MODELS_DIR="$HOME/.llm-models"
mkdir -p "$MODELS_DIR"

# Download helper
download_file() {
    local url=$1
    local dest=$2
    if [ -f "$dest" ]; then
        echo "$(basename "$dest") already exists, skipping."
        return
    fi
    echo "Downloading $(basename "$dest")..."
    if command -v wget >/dev/null 2>&1; then
        wget -c --show-progress -O "$dest" "$url"
    elif command -v curl >/dev/null 2>&1; then
        curl -L -C - -o "$dest" "$url"
    else
        echo "Error: Neither wget nor curl is installed. Please install one to download the models."
        exit 1
    fi
}

echo "Starting model downloads for Ask AI..."

# 1. Qwen 2.5 1.5B Instruct (Q4_K_M)
download_file \
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf" \
    "$MODELS_DIR/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"

# 2. Llama 3.2 3B Instruct (Q4_K_M)
download_file \
    "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf" \
    "$MODELS_DIR/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

echo "All models downloaded successfully!"
