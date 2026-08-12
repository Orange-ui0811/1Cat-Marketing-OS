#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
requested=${1:-all}
version=0.1.0

custom_images="1cat/runtime-api:0.1.0 1cat/runtime-worker:0.1.0 1cat/organization-mcp:0.1.0 1cat/workspace:0.1.0 1cat/caddy:2.10.2 1cat/hermes-agent:0.20.0 1cat/egress-proxy:0.1.0 1cat/model-gateway:0.1.0"
third_party_images="pgvector/pgvector:pg16 minio/minio:RELEASE.2025-04-22T22-12-26Z quay.io/keycloak/keycloak:26.3.3 alpine:3.22"
all_images="$custom_images $third_party_images"

pull_runtime_images() {
  arch=$1
  case "$arch" in
    arm64)
      pg_digest=386f17b2364a613752d23b4e23c6e27b87b2997b3ac3ea23dac42df579670524
      minio_digest=54d3d6a0a58fb25b4e9943d1db3828d3b4de44666f911381b4fda57175488194
      keycloak_digest=16d2321732b7daa01cae0f98d34e069869703c298b6751b0c83472603effc80f
      alpine_digest=2c9d26f410d032d5b1525aa8a873e238b05b90c4ae8618743d4311f0cc827e37
      ;;
    amd64)
      pg_digest=84a355869251af1a3379cfc9fa7b4dbf962c03f642a4bb7b339a203925071c43
      minio_digest=3f97c5651cb6662b880c787a232b6b34fec8d8922e08d6617b25d241a21164bb
      keycloak_digest=b67f53e348e6e09a5deabfe860f770565d589e39183a73818367206801ba7912
      alpine_digest=7c8cb692ae09657cbc4a3f3cbd0e8d5a2690ba38386aaaf252dbb060bf5eb2e6
      ;;
  esac
  docker pull "pgvector/pgvector@sha256:$pg_digest"
  docker tag "pgvector/pgvector@sha256:$pg_digest" pgvector/pgvector:pg16
  docker pull "minio/minio@sha256:$minio_digest"
  docker tag "minio/minio@sha256:$minio_digest" minio/minio:RELEASE.2025-04-22T22-12-26Z
  docker pull "quay.io/keycloak/keycloak@sha256:$keycloak_digest"
  docker tag "quay.io/keycloak/keycloak@sha256:$keycloak_digest" quay.io/keycloak/keycloak:26.3.3
  docker pull "alpine@sha256:$alpine_digest"
  docker tag "alpine@sha256:$alpine_digest" alpine:3.22
}

build_runtime_images() {
  arch=$1
  pull_runtime_images "$arch"
  DOCKER_DEFAULT_PLATFORM="linux/$arch" docker compose --env-file .env --profile agents --profile api-key build \
    runtime-api runtime-worker organization-mcp workspace caddy hermes-pma egress-proxy model-gateway
  for image in $all_images; do
    actual=$(docker image inspect "$image" --format '{{.Architecture}}')
    [ "$actual" = "$arch" ] || { echo "$image 架构错误：$actual != $arch"; exit 1; }
  done
}

write_evidence() {
  bundle=$1
  arch=$2
  mkdir -p "$bundle/evidence/sbom" "$bundle/evidence/vulnerability"
  docker image inspect $all_images > "$bundle/evidence/image-inspect.json"
  for image in $custom_images; do
    safe=$(printf '%s' "$image" | tr '/:' '__')
    docker scout sbom --format spdx --output "$bundle/evidence/sbom/$safe.spdx.json" "local://$image"
    if command -v trivy >/dev/null 2>&1; then
      trivy image --scanners vuln --format sarif --output "$bundle/evidence/vulnerability/$safe.sarif.json" "$image"
    elif ! docker scout cves --format sarif --output "$bundle/evidence/vulnerability/$safe.sarif.json" "local://$image"; then
      printf '%s\n' \
        "status=not_executed" \
        "reason=Docker Scout vulnerability service requires an authenticated Docker account" \
        "artifact=$image" > "$bundle/evidence/vulnerability/$safe.status.txt"
    fi
  done
  printf '%s\n' "platform=linux/$arch" "generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$bundle/evidence/build.txt"
}

package_source() {
  mkdir -p dist
  source_file="dist/1cat-hermes-os-r0-v${version}-source.tar.zst"
  tar --no-read-sparse --exclude='./.git' --exclude='./.env' --exclude='./.runtime' --exclude='./.venv' --exclude='./dist' \
      --exclude='./.DS_Store' --exclude='*/.DS_Store' \
      --exclude='./apps/workspace/node_modules' --exclude='./apps/workspace/dist' \
      --exclude='./apps/workspace/test-results' --exclude='./apps/workspace/playwright-report' \
      --exclude='*/__pycache__/*' --exclude='*.pyc' --exclude='*.pyo' \
      -cf - . | zstd -T0 -10 -f -o "$source_file"
}

package_platform() {
  arch=$1
  case "$arch" in arm64|amd64) ;; *) echo "unsupported architecture: $arch"; exit 2;; esac
  bundle=".runtime/package-$arch"
  mkdir -p "$bundle"
  find "$bundle" -mindepth 1 -delete
  build_runtime_images "$arch"
  docker save $all_images | zstd -T0 -7 -f -o "$bundle/images.tar.zst"
  cp compose.yaml .env.example README.md pyproject.toml Makefile "$bundle/"
  sed -E 's/@sha256:[a-f0-9]{64}//g' "$bundle/compose.yaml" > "$bundle/compose.release.yaml"
  mv "$bundle/compose.release.yaml" "$bundle/compose.yaml"
  cp -R apps bin docs fixtures infra packages profiles scripts "$bundle/"
  find "$bundle/apps/workspace/node_modules" -mindepth 1 -delete 2>/dev/null || true
  find "$bundle/apps/workspace/dist" -mindepth 1 -delete 2>/dev/null || true
  find "$bundle/apps/workspace/test-results" -mindepth 1 -delete 2>/dev/null || true
  rmdir "$bundle/apps/workspace/node_modules" "$bundle/apps/workspace/dist" \
        "$bundle/apps/workspace/test-results" 2>/dev/null || true
  find "$bundle" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
  find "$bundle" -type f -name '.DS_Store' -delete
  mkdir -p "$bundle/vendor/hermes-agent"
  cp vendor/hermes-agent/UPSTREAM_COMMIT "$bundle/vendor/hermes-agent/UPSTREAM_COMMIT"
  cp scripts/release_install.sh "$bundle/install.sh"
  chmod +x "$bundle/install.sh" "$bundle/bin/1cat"
  : > "$bundle/.release-bundle"
  write_evidence "$bundle" "$arch"
  (cd "$bundle" && shasum -a 256 images.tar.zst > IMAGE_SHA256SUMS)
  tar --no-read-sparse -C "$bundle" -cf - . | zstd -T0 -10 -f -o "dist/1cat-hermes-os-r0-v${version}-linux-${arch}.tar.zst"
}

command -v zstd >/dev/null || { echo "打包需要zstd"; exit 1; }
command -v docker >/dev/null || { echo "打包需要Docker"; exit 1; }
mkdir -p dist
case "$requested" in
  arm64|amd64) package_platform "$requested"; package_source ;;
  all) package_platform arm64; package_platform amd64; package_source ;;
  *) echo "用法：./scripts/package.sh arm64|amd64|all"; exit 2 ;;
esac
shasum -a 256 dist/*.tar.zst | sed 's#  dist/#  #' > dist/SHA256SUMS
echo "部署包、源码包、SBOM和校验文件已生成到 dist/"
