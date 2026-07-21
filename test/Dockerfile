# Freehold OS boot-test harness.
# Boots the built ISO in QEMU and serves the virtual display over noVNC,
# so the boot can be watched in any browser at http://localhost:6080/vnc.html
FROM debian:trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
        qemu-system-x86 \
        qemu-utils \
        novnc \
        websockify \
        socat \
        imagemagick \
    && rm -rf /var/lib/apt/lists/*

COPY entry.sh /entry.sh
EXPOSE 6080
CMD ["sh", "/entry.sh"]
