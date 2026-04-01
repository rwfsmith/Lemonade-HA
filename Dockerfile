ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /usr/src
ARG LEMONADE_HA_VERSION
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

# Install the Lemonade bridge
COPY lemonade_bridge/ /usr/src/lemonade_bridge/
COPY pyproject.toml /usr/src/
COPY requirements.txt /usr/src/
COPY custom_components/ /usr/src/custom_components/

RUN pip3 install --no-cache-dir \
        -r /usr/src/requirements.txt \
        /usr/src

# Copy rootfs (s6-overlay service definitions)
WORKDIR /
COPY rootfs /

# Health-check: just verify the STT port is listening.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD nc -z localhost 10500 || exit 1
