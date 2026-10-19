#!/usr/bin/env bash
# scripts/orfs_container.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORFS_ROOT="${ORFS_ROOT:-$PROJECT_ROOT/OpenROAD-flow-scripts}"
IMAGE_FILE="$PROJECT_ROOT/toolchain/orfs-image.txt"
GUI=0

if [[ "${1:-}" == "--gui" ]]; then
  GUI=1
  shift
fi

[[ $# -gt 0 ]] || { echo "usage: $0 [--gui] COMMAND..." >&2; exit 2; }
[[ -f "$IMAGE_FILE" ]] || { echo "missing $IMAGE_FILE" >&2; exit 2; }
[[ -f "$ORFS_ROOT/flow/Makefile" ]] || {
  echo "missing ORFS flow at $ORFS_ROOT/flow" >&2
  exit 2
}

IMAGE="$(<"$IMAGE_FILE")"
DOCKER_ARGS=(
  run --rm -i
  --user "$(id -u):$(id -g)"
  -e HOME=/tmp
  -e WORK_HOME=/work
  -v "$PROJECT_ROOT:/work"
  -v "$ORFS_ROOT/flow:/OpenROAD-flow-scripts/flow"
  -w /OpenROAD-flow-scripts/flow
)

if [[ "$GUI" == 1 ]]; then
  [[ -n "${DISPLAY:-}" ]] || { echo "DISPLAY is not set" >&2; exit 2; }
  DOCKER_ARGS+=(
    -e "DISPLAY=$DISPLAY"
    -e QT_X11_NO_MITSHM=1
    -v /tmp/.X11-unix:/tmp/.X11-unix
    --network host
  )
fi

exec docker "${DOCKER_ARGS[@]}" "$IMAGE" \
  bash -lc 'source /OpenROAD-flow-scripts/env.sh; exec "$@"' bash "$@"
