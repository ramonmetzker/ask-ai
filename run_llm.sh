#!/bin/bash

# Simple script to run local LLM models using llama.cpp and CUDA GPU

# Exit immediately if a command exits with a non-zero status
set -e

# Models directory
MODELS_DIR="$HOME/.llm-models"

# Models
QWEN_MODEL="$MODELS_DIR/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
LLAMA_MODEL="$MODELS_DIR/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
LLAMA_XS_MODEL="$MODELS_DIR/Llama-3.2-3B-Instruct-Q2_K.gguf"

# Locate llama-completion binary
if command -v llama-completion >/dev/null 2>&1; then
    BINARY="llama-completion"
elif [ -f "$HOME/ai/llama.cpp/build/bin/llama-completion" ]; then
    BINARY="$HOME/ai/llama.cpp/build/bin/llama-completion"
else
    echo "Error: llama-completion binary not found in PATH or at ~/ai/llama.cpp/build/bin/llama-completion"
    echo "Please build llama.cpp first."
    exit 1
fi

# Print usage
usage() {
    echo "Usage: $0 [model_type] [prompt]"
    echo "  model_type: 'qwen' (default), 'llama', 'llama-xs'"
    echo "  prompt:     The prompt to send to the model (in quotes)"
    echo ""
    echo "Examples:"
    echo "  $0 qwen \"Why is the sky blue?\""
    echo "  $0 llama-xs \"Write a python function to check if a number is prime.\""
    echo ""
    echo "If no arguments are provided, you will be prompted interactively."
    exit 1
}

MODEL_CHOICE=""
PROMPT=""

if [ "$#" -ge 1 ]; then
    if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
        usage
    fi
    MODEL_CHOICE="$1"
    shift
    PROMPT="$*"
fi

# Interactive selection if arguments not fully provided
if [ -z "$MODEL_CHOICE" ]; then
    echo "Select a model to run on your GPU:"
    echo "1) Qwen 2.5 - 1.5B Instruct (Q4_K_M) [~940 MB VRAM, very fast]"
    echo "2) Llama 3.2 - 3B Instruct (Q4_K_M) [~2.0 GB VRAM, smarter]"
    echo "3) Llama 3.2 - 3B Instruct (Q2_K) [~1.3 GB VRAM, smarter, extra small]"
    read -p "Choose option (1-3) [default 1]: " opt
    case "$opt" in
        2) MODEL_CHOICE="llama" ;;
        3) MODEL_CHOICE="llama-xs" ;;
        *) MODEL_CHOICE="qwen" ;;
    esac
fi

# Set model path and template based on choice
if [ "$MODEL_CHOICE" == "qwen" ]; then
    SELECTED_MODEL="$QWEN_MODEL"
    MODEL_NAME="Qwen 2.5 1.5B"
    # Format Qwen ChatML template
    FORMATTED_PROMPT="<|im_start|>system
You are a helpful assistant.<|im_end|>
<|im_start|>user
$PROMPT<|im_end|>
<|im_start|>assistant
"
elif [ "$MODEL_CHOICE" == "llama" ]; then
    SELECTED_MODEL="$LLAMA_MODEL"
    MODEL_NAME="Llama 3.2 3B"
    # Format Llama 3/3.2 template
    FORMATTED_PROMPT="<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>

$PROMPT<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"
elif [ "$MODEL_CHOICE" == "llama-xs" ]; then
    SELECTED_MODEL="$LLAMA_XS_MODEL"
    MODEL_NAME="Llama 3.2 3B (XS)"
    # Format Llama 3/3.2 template
    FORMATTED_PROMPT="<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>

$PROMPT<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"
else
    echo "Error: Unknown model choice '$MODEL_CHOICE'. Use 'qwen', 'llama', or 'llama-xs'."
    exit 1
fi

# Verify model file exists
if [ ! -f "$SELECTED_MODEL" ]; then
    echo "Error: Model file not found at $SELECTED_MODEL"
    exit 1
fi

# Interactive prompt if not provided
if [ -z "$PROMPT" ]; then
    echo ""
    read -p "Enter prompt for $MODEL_NAME: " PROMPT
    # Format it after reading
    if [ "$MODEL_CHOICE" == "qwen" ]; then
        FORMATTED_PROMPT="<|im_start|>system
You are a helpful assistant.<|im_end|>
<|im_start|>user
$PROMPT<|im_end|>
<|im_start|>assistant
"
    else
        FORMATTED_PROMPT="<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>

$PROMPT<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"
    fi
fi

# Run the model, silence stderr, strip end-of-text marker
"$BINARY" \
    -m "$SELECTED_MODEL" \
    -ngl 99 \
    -no-cnv \
    --no-display-prompt \
    -p "$FORMATTED_PROMPT" \
    2>/dev/null | perl -0777 -pe 's/ \[end of text\]//g; s/\s+$/\n/'
