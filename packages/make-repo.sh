#!/bin/sh
# Dagric OS — SUPERSEDED. This script must not run. Use packages/build-repo.sh.
#
# It is kept as a refusal rather than deleted because `repo.ps1` invoked it and
# somebody may still type that from habit — and a script that quietly does the
# wrong thing to a signing key is worse than one that is missing.
#
# What it used to do, and why both halves are wrong now:
#
#   1. IT MINTED A SECOND SIGNING KEY. On any host where /keys/gnupg had no
#      "Dagric OS Repository" secret key it generated a fresh 4096-bit RSA key
#      and signed the repository with it. The real channel is signed by
#      6CE37402BA0A0EF8, and that key is what every shipped machine trusts via
#      /usr/share/keyrings/dagric.gpg. A repository signed by any other key is
#      one that no Dagric installation on earth will accept — apt rejects it as
#      unsigned. Worse, the new key lived in a Docker volume, so the failure was
#      invisible until an owner's `apt update` started erroring. See the "ONE
#      KEY, NOT TWO" note at the top of build-repo.sh, which was written about
#      exactly this script.
#
#   2. IT PRODUCED A LAYOUT APT CANNOT READ HERE. It wrote a flat repository
#      (Packages and Release at the root, consumed as `deb https://HOST/ ./`).
#      The shipped sources.list.d/dagric.list asks for a SUITE layout:
#          deb [signed-by=...] https://dagric-os.web.app/repo trixie main
#      which needs dists/trixie/main/binary-amd64/. The flat layout answers that
#      request with 404s.
#
# The live path is packages/build-repo.sh, which uses the existing key and the
# suite layout, and which builds its packages through stage-packages.sh so the
# ISO and the channel are assembled from the same source.
echo "make-repo.sh is superseded and will not run." >&2
echo >&2
echo "It generated a SECOND repository signing key and a flat repo layout that" >&2
echo "the shipped sources.list cannot read. Every machine already trusts" >&2
echo "6CE37402BA0A0EF8; a repo signed by anything else is rejected as unsigned." >&2
echo >&2
echo "Use instead:  sh packages/build-repo.sh" >&2
exit 1
