#!/usr/bin/env bash
set -euo pipefail

CONTENT_DIR="$(cd "$(dirname "$0")/../content" && pwd)"

HASH=$(find "$CONTENT_DIR" -type f \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  | sort \
  | xargs md5sum \
  | md5sum \
  | awk '{print $1}')

echo "{\"md5\": \"$HASH\"}"
