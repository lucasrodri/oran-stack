#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 COMPONENT SOURCE_DIR OUTPUT_FILE IMAGE_PREFIX" >&2
  exit 2
fi

component="$1"
source_dir="$2"
output_file="$3"
image_prefix="$4"

ubuntu_builder="${image_prefix}/ric-build-base-ubuntu:m-amd64"
alpine_builder="${image_prefix}/ric-build-base-alpine:m-amd64"

case "$component" in
  a1|appmgr|rtmgr|submgr)
    context="$source_dir"
    dockerfile="$source_dir/Dockerfile"
    ;;
  dbaas)
    context="$source_dir"
    dockerfile="$source_dir/docker/Dockerfile.redis"
    ;;
  e2)
    context="$source_dir/RIC-E2-TERMINATION"
    dockerfile="$context/Dockerfile"
    ;;
  e2mgr)
    context="$source_dir/E2Manager"
    dockerfile="$context/Dockerfile"
    ;;
  *)
    echo "unsupported RIC component: $component" >&2
    exit 2
    ;;
esac

if [[ ! -f "$dockerfile" ]]; then
  echo "upstream Dockerfile not found: $dockerfile" >&2
  exit 1
fi

# Only replace the two unavailable O-RAN builder images. Runtime images and
# component sources remain exactly those declared by the pinned M-release
# commit. The M-release Dockerfiles are amd64-specific, so this pipeline is
# deliberately linux/amd64 until RMR/SDL are rebuilt from source for ARM64.
sed -i.bak \
  -e "s|nexus3\.o-ran-sc\.org:10002/o-ran-sc/bldr-ubuntu22-c-go:1\.0\.0|${ubuntu_builder}|g" \
  -e "s|nexus3\.o-ran-sc\.org:10002/o-ran-sc/bldr-alpine3-go:2\.0\.0|${alpine_builder}|g" \
  "$dockerfile"
rm -f "${dockerfile}.bak"

if grep -Eq 'nexus3\.o-ran-sc\.org:[0-9]+/o-ran-sc/bldr-(ubuntu22-c-go|alpine3-go)' "$dockerfile"; then
  echo "an unavailable Nexus builder reference remains in $dockerfile" >&2
  exit 1
fi

{
  echo "context=$context"
  echo "dockerfile=$dockerfile"
} >> "$output_file"
