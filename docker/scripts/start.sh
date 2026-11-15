#!/usr/bin/env bash
set -Eeuo pipefail

image_repository="${HAWKING_IMAGE_REPOSITORY:-ghcr.io/naschorr/hawking}"
image_tag="${HAWKING_IMAGE_TAG:-latest}"
previous_tag="${HAWKING_PREVIOUS_TAG:-previous}"
image="${HAWKING_IMAGE:-${image_repository}:${image_tag}}"
previous_image="${HAWKING_PREVIOUS_IMAGE:-${image_repository}:${previous_tag}}"
pull_image="${HAWKING_PULL_IMAGE:-true}"
container_name="${HAWKING_CONTAINER_NAME:-hawking}"
data_dir="${HAWKING_DATA_DIR:-/opt/hawking}"
config_dir="${HAWKING_CONFIG_DIR:-${data_dir}/configuration}"
env_file="${HAWKING_ENV_FILE:-${config_dir}/.env}"
platform="${HAWKING_PLATFORM:-linux/amd64}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script with sudo." >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed or is not on PATH." >&2
    exit 1
fi

if command -v systemctl >/dev/null 2>&1; then
    systemctl enable --now docker
fi

mkdir -p "${config_dir}"
config_dir="$(cd "${config_dir}" && pwd -P)"

if [[ ! -f "${config_dir}/config.json" ]]; then
    echo "Missing config file: ${config_dir}/config.json." >&2
    exit 1
fi

if [[ ! -f "${env_file}" ]]; then
    echo "Missing env file: ${env_file}." >&2
    exit 1
fi
env_file="$(realpath "${env_file}")"
chmod 600 "${env_file}"

docker info >/dev/null

current_image_id=""
if docker container inspect "${container_name}" >/dev/null 2>&1; then
    container_running="$(docker container inspect --format '{{.State.Running}}' "${container_name}")"
    if [[ "${container_running}" == "true" ]]; then
        current_image_id="$(docker container inspect --format '{{.Image}}' "${container_name}")"
    fi
fi

case "${pull_image}" in
    true)
        docker pull --platform "${platform}" "${image}"
        ;;
    false)
        ;;
    *)
        echo "HAWKING_PULL_IMAGE must be 'true' or 'false'." >&2
        exit 1
        ;;
esac

target_image_id="$(docker image inspect --format '{{.Id}}' "${image}")"
if [[ -n "${current_image_id}" && "${current_image_id}" != "${target_image_id}" && "${image}" != "${previous_image}" ]]; then
    docker image tag "${current_image_id}" "${previous_image}"
fi

docker volume create hawking-logs >/dev/null
docker volume create hawking-privacy >/dev/null

if docker container inspect "${container_name}" >/dev/null 2>&1; then
    docker container rm --force "${container_name}" >/dev/null
fi

docker run --detach \
    --platform "${platform}" \
    --name "${container_name}" \
    --init \
    --restart unless-stopped \
    --env-file "${env_file}" \
    --mount "type=bind,source=${config_dir},target=/app/configuration,readonly" \
    --mount type=volume,source=hawking-logs,target=/app/logs \
    --mount type=volume,source=hawking-privacy,target=/app/privacy \
    "${target_image_id}"

docker image prune --force

echo "Started ${container_name} from ${image}."