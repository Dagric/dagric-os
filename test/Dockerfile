# Dagric OS boot-test harness.
# Boots the built ISO in QEMU and serves the virtual display over noVNC,
# so the boot can be watched in any browser at http://localhost:6080/vnc.html
# Includes vncdotool for scripted mouse/keyboard input (install testing).
# Pin the test harness base by digest.  The tag remains for readability, while
# the digest prevents an upstream tag move from silently changing the QEMU/VNC
# environment that release evidence is produced in.
FROM debian:trixie@sha256:fac46bff2e02f51425b6e33b0e1169f55dfb053d83511ca28aa50c09fd5ed7a4

RUN apt-get update && apt-get install -y --no-install-recommends \
        qemu-system-x86 \
        qemu-utils \
        novnc \
        websockify \
        socat \
        imagemagick \
        python3-pip \
        ovmf \
    && pip3 install --break-system-packages 'vncdotool==1.3.0' \
    && rm -rf /var/lib/apt/lists/*

COPY entry.sh /entry.sh
COPY vm-keys.sh /vm-keys.sh
COPY vm-mon.sh /vm-mon.sh
COPY vm-vclick.sh /vm-vclick.sh
COPY vm-vtype.sh /vm-vtype.sh
EXPOSE 6080
CMD ["sh", "/entry.sh"]
