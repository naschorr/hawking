#!/usr/bin/env bash
set -Eeuo pipefail

container_name="${HAWKING_CONTAINER_NAME:-hawking}"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed or is not on PATH." >&2
    exit 1
fi

if ! docker container inspect "${container_name}" >/dev/null 2>&1; then
    echo "Container ${container_name} does not exist; nothing to stop."
    exit 0
fi

docker container update --restart=no "${container_name}" >/dev/null

if [[ "$(docker container inspect --format '{{.State.Running}}' "${container_name}")" != "true" ]]; then
    echo "Container ${container_name} is stopped and will not restart automatically."
    exit 0
fi

docker container stop "${container_name}"