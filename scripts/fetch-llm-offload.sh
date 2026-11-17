#!/bin/sh
# Clone llm-offload read-only at the commit this benchmark was measured against.
set -eu
cd "$(dirname "$0")/.."
COMMIT=c0eb687a7bf89e896c53ce0de2a35eb4652390c2
if [ ! -d .deps/llm-offload/.git ]; then
  git clone --quiet https://github.com/oguzhanozfe/llm-offload.git .deps/llm-offload
fi
git -C .deps/llm-offload checkout --quiet "$COMMIT"
echo "llm-offload at $COMMIT"
