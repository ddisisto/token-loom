#!/usr/bin/env bash
# Serve a local base model over llama.cpp's own server binary.
#
# This is the only setup that returns raw continuation *and* logprobs at once;
# every hosted provider forces a choice between the two.
#
# The --alias is what /props reports as model_alias, and the stack names a tree's
# vocabulary by it. It is *not* the source name: that has to separate anything whose
# draws must not factor together, so it defaults to the model file's stem instead.
set -euo pipefail

REPO=${REPO:-mradermacher/Qwen2.5-7B-i1-GGUF}
FILE=${FILE:-Qwen2.5-7B.i1-Q4_K_M.gguf}
ALIAS=${ALIAS:-qwen2.5-7b-base}
PORT=${PORT:-8081}     # the spike server holds 8080
CTX=${CTX:-16384}      # ~0.9GB of KV cache, leaving room for the 4.7GB of weights

# no-op once cached, and prints the resolved path either way. -q is load-bearing:
# without it the path arrives decorated as 'path=/...' and llama-server takes that
# whole string as the filename.
MODEL=$(hf download -q "$REPO" "$FILE")

exec llama-server \
    --model "$MODEL" \
    --alias "$ALIAS" \
    --port "$PORT" \
    --ctx-size "$CTX" \
    --n-gpu-layers 99 \
    --parallel 1 \
    "$@"
