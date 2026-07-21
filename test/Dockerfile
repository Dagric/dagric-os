# Freehold OS boot-test harness.
# Boots the built ISO in QEMU and serves the virtual display over noVNC,
# so the boot can be watched in any browser at http://localhost:6080/vnc.html
# Includes vncdotool for scripted mouse/keyboard input (install testing).
FROM debian:trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
        qemu-system-x86 \
        qemu-utils \
        novnc \
        websockify \
        socat \
        imagemagick \
        python3-pip \
    && pip3 install --break-system-packages vncdotool \
    && rm -rf /var/lib/apt/lists/*

COPY entry.sh /entry.sh
COPY vm-keys.sh /vm-keys.sh
COPY vm-mon.sh /vm-mon.sh
COPY vm-vclick.sh /vm-vclick.sh
COPY vm-vtype.sh /vm-vtype.sh
EXPOSE 6080
CMD ["sh", "/entry.sh"]
