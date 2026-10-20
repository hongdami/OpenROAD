#!/usr/bin/env bash
# scripts/check_environment.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIRED_KIB=$((20 * 1024 * 1024))

command -v docker >/dev/null || { echo "docker is not installed" >&2; exit 1; }
docker info >/dev/null
[[ -s "$PROJECT_ROOT/toolchain/orfs-image.txt" ]]
[[ -s "$PROJECT_ROOT/toolchain/orfs-commit.txt" ]]
PINNED_COMMIT="$(tr -d '[:space:]' < "$PROJECT_ROOT/toolchain/orfs-commit.txt")"
CHECKOUT_COMMIT="$(git -C "$PROJECT_ROOT/OpenROAD-flow-scripts" rev-parse HEAD)" || {
  echo "cannot read OpenROAD-flow-scripts revision" >&2
  exit 1
}
if [[ "$PINNED_COMMIT" != "$CHECKOUT_COMMIT" ]]; then
  echo "ORFS checkout $CHECKOUT_COMMIT does not match pin $PINNED_COMMIT" >&2
  exit 1
fi

AVAILABLE_KIB="$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print $4}')"
if (( AVAILABLE_KIB < REQUIRED_KIB )); then
  echo "at least 20 GiB free space is required" >&2
  exit 1
fi

IMAGE="$(<"$PROJECT_ROOT/toolchain/orfs-image.txt")"
docker image inspect "$IMAGE" >/dev/null
mkdir -p "$PROJECT_ROOT/work"
{
  printf 'orfs_scripts_commit=%s\n' \
    "$(<"$PROJECT_ROOT/toolchain/orfs-commit.txt")"
  printf 'orfs_image=%s\n' "$IMAGE"
  "$PROJECT_ROOT/scripts/orfs_container.sh" bash -c \
    'yosys -V; openroad -version; klayout -v'
} | tee "$PROJECT_ROOT/work/toolchain-versions.txt"
