ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# custom_components to deploy into HA config dir
COPY custom_components/ /usr/src/custom_components/

# Copy rootfs (s6-overlay service definitions)
WORKDIR /
COPY rootfs /
