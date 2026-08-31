#!/bin/sh
set -e
curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh
cd /work
wasm-pack build --target web --release
ls -la pkg
