#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAYER_DIR="$SCRIPT_DIR/layer"
OUTPUT="$SCRIPT_DIR/bcrypt-layer.zip"

rm -rf "$LAYER_DIR" "$OUTPUT"
mkdir -p "$LAYER_DIR/python"

docker run --rm \
  --entrypoint pip \
  -u "$(id -u):$(id -g)" \
  -v "$LAYER_DIR/python:/out" \
  public.ecr.aws/lambda/python:3.14 \
  install bcrypt -t /out

cd "$LAYER_DIR"
zip -r "$OUTPUT" python/
rm -rf "$LAYER_DIR"

echo "Layer built: $OUTPUT"
