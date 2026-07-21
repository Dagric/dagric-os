# Dagric OS build environment.
# live-build needs a Debian host; this container IS that host.
FROM debian:trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
        live-build \
        ca-certificates \
        rsync \
        xorriso \
        mtools \
        dosfstools \
        squashfs-tools \
        dpkg-dev \
        apt-utils \
        gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
