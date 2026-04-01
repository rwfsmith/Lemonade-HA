ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /usr/src
ARG WYOMING_LEMONADE_VERSION
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Install system deps
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        netcat-traditional \
        python3 \
        python3-dev \
        python3-pip \
    && pip3 install --no-cache-dir -U \
        setuptools \
        wheel \
    && rm -rf /var/lib/apt/lists/*

# Install the Wyoming-Lemonade bridge
COPY wyoming_lemonade/ /usr/src/wyoming_lemonade/
COPY pyproject.toml /usr/src/
COPY requirements.txt /usr/src/

RUN pip3 install --no-cache-dir \
        -r /usr/src/requirements.txt \
        /usr/src

# Copy rootfs (s6-overlay service definitions)
WORKDIR /
COPY rootfs /

# Health-check: ports open immediately; use a short start-period so HA
# Supervisor sees the container as healthy well within its 120-second window.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10500 \
        | grep -q "lemonade" \
        || exit 1
