# Dagric OS build environment.
# live-build needs a Debian host; this container IS that host.
FROM debian:trixie

# gettext is here for msgfmt, and only for msgfmt. It is a build-HOST package:
# it runs against the tree in container-build.sh and never reaches the image,
# which already carries gettext-base for the runtime and wants nothing more.
#
# Without it container-build.sh always took the "msgfmt not installed" branch,
# so the gate that catches a stale .mo was dead on every CI build of both
# editions and only ever fired on a developer laptop that happened to have
# gettext. That is not theoretical: the catalogues sat two consent strings
# behind po/*.po — the NVIDIA proprietary-driver prompt and the Variety
# privacy screen, English in all five languages — and CI would have shipped
# them in a release ISO without a word. "A skipped check costs nothing" was
# only ever true while the check had never been needed.
#
# curl is here for container-build.sh's update-channel collision gate, which
# fetches the published Packages index over HTTPS before starting a build. The
# image never had an HTTP client - debian:trixie ships none, and none of the
# packages below pulls one in under --no-install-recommends - so `curl` was
# simply not found, the substitution came back empty, and the gate took its
# "could not reach the update channel" SKIP branch on every CI and release run.
# The one check written to turn a twenty-minute build death into a five-second
# error had never once run there, and it printed a WARNING every time, which is
# how a reader learns to ignore warnings. (ca-certificates was already present
# for it, with nothing to use it.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        live-build \
        ca-certificates \
        curl \
        rsync \
        xorriso \
        mtools \
        dosfstools \
        squashfs-tools \
        dpkg-dev \
        apt-utils \
        gnupg \
        gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
