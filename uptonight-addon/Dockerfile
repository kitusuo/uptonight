# Thin add-on layer on top of the published, multi-arch UpTonight image.
# Building the scientific stack on the HA device would be impractical, so the
# heavy work stays in the base image; this only adds bashio + the entry script.
ARG BUILD_FROM=ghcr.io/kitusuo/uptonight:latest
FROM ${BUILD_FROM}

ARG BASHIO_VERSION=v0.16.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq curl ca-certificates \
    && mkdir -p /usr/lib/bashio \
    && curl -fsSL "https://github.com/hassio-addons/bashio/archive/refs/tags/${BASHIO_VERSION}.tar.gz" \
        | tar -xzf - --strip-components=1 -C /usr/lib/bashio \
    && ln -s /usr/lib/bashio/lib/bashio.sh /usr/bin/bashio \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Override the base image's /app/main entrypoint - the add-on runs run.sh,
# which generates the config and then launches UpTonight.
ENTRYPOINT []
CMD ["/run.sh"]
