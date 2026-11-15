#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage: stop.sh [OPTIONS]

Options:
  --container-name NAME  Container name (default: hawking)
  -h, --help             Show this help

The container name can also be set with HAWKING_CONTAINER_NAME.
EOF
}

container_name="${HAWKING_CONTAINER_NAME:-hawking}"

while (($# > 0)); do
    case "$1" in
        --container-name)
            if [[ -z "${2:-}" || "${2:-}" == --* ]]; then
                echo "$1 requires a value." >&2
                usage >&2
                exit 2
            fi
            container_name="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

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