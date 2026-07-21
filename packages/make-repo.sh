#!/bin/sh
# Dagric OS — turn /out/repo into a signed APT repository.
# Expects packages in /out/repo/pool (run build-packages.sh first).
# The signing key lives in /keys (persisted outside the repo, never committed);
# it is generated on first run.
set -e

REPO=/out/repo
export GNUPGHOME=/keys/gnupg
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

# One-time: generate the repository signing key.
if ! gpg --list-secret-keys "Dagric OS Repository" >/dev/null 2>&1; then
    echo "Generating repository signing key (one-time)..."
    gpg --batch --gen-key << 'EOF'
%no-protection
Key-Type: RSA
Key-Length: 4096
Name-Real: Dagric OS Repository
Name-Email: repo@example.org
Expire-Date: 0
%commit
EOF
fi

cd "$REPO"
dpkg-scanpackages --multiversion pool > Packages
gzip -kf Packages
apt-ftparchive release . > Release
gpg --default-key "Dagric OS Repository" -abs -o Release.gpg Release
gpg --default-key "Dagric OS Repository" --clearsign -o InRelease Release
gpg --export --armor "Dagric OS Repository" > dagric-repo.gpg.asc

echo ""
echo "Signed APT repo ready at out/repo. Serve it over HTTPS, then on clients:"
echo "  curl -fsSL https://YOUR-HOST/dagric-repo.gpg.asc | gpg --dearmor -o /usr/share/keyrings/dagric.gpg"
echo "  echo 'deb [signed-by=/usr/share/keyrings/dagric.gpg] https://YOUR-HOST/ ./' > /etc/apt/sources.list.d/dagric.list"
