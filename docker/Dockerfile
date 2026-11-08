# syntax=docker/dockerfile:1
FROM python:3.15-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WINEDEBUG=-all \
    WINEPREFIX=/home/hawking/.wine

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        wine \
        wine32:i386 \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential libffi-dev \
    && python -m pip install -r requirements.txt \
    && apt-get purge -y build-essential libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm requirements.txt

COPY code ./code

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && mkdir -p code/addons/phrases/phrases \
    && curl --fail --location --silent --show-error --retry 3 \
        https://github.com/naschorr/hawking-phrases/archive/refs/heads/master.tar.gz \
        --output /tmp/hawking-phrases.tar.gz \
    && tar -xzf /tmp/hawking-phrases.tar.gz --strip-components=1 -C code/addons/phrases/phrases \
    && rm /tmp/hawking-phrases.tar.gz \
    && test -n "$(find code/addons/phrases/phrases -maxdepth 1 -type f -name '*.json' -print -quit)" \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin hawking \
    && mkdir -p logs privacy temp \
    && mkdir -p /tmp/runtime-hawking /tmp/.X11-unix /home/hawking/.wine \
    && chmod 700 /tmp/runtime-hawking \
    && chmod 1777 /tmp/.X11-unix \
    && chown -R hawking:hawking . /tmp/runtime-hawking /home/hawking/.wine \
    && su -s /bin/sh hawking -c 'WINEPREFIX=/home/hawking/.wine WINEDEBUG=-all XDG_RUNTIME_DIR=/tmp/runtime-hawking xvfb-run -a wineboot --init' \
    && rm -rf /tmp/runtime-hawking

COPY docker/entrypoint.sh /usr/local/bin/hawking-entrypoint
RUN chmod 755 /usr/local/bin/hawking-entrypoint

ENV DISPLAY=:0.0
USER hawking

ENTRYPOINT ["/usr/local/bin/hawking-entrypoint"]