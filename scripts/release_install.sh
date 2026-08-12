#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
[ -f .release-bundle ] || { echo "这不是1Cat离线部署包"; exit 2; }
command -v docker >/dev/null || { echo "缺少Docker"; exit 2; }
docker info >/dev/null 2>&1 || { echo "Docker尚未启动"; exit 2; }
command -v zstd >/dev/null || { echo "缺少zstd"; exit 2; }
shasum -a 256 -c IMAGE_SHA256SUMS
zstd -dc images.tar.zst | docker load
./bin/1cat doctor
./bin/1cat init
echo "离线镜像已加载。运行 ./bin/1cat up 启动，随后执行 ./bin/1cat smoke。"

