# Dagric OS - SUPERSEDED. This script must not run. Use packages/build-repo.sh.
#
# Kept as a refusal rather than deleted, because it was the documented entry
# point for building the update channel and is the thing somebody types from
# habit. It called build-packages.sh and make-repo.sh, and make-repo.sh minted a
# SECOND repository signing key whenever the Docker volume was empty.
#
# That matters more than it sounds. Every Dagric machine trusts exactly one key,
# 6CE37402BA0A0EF8, shipped as /usr/share/keyrings/dagric.gpg. A repository
# signed by any other key is rejected by apt as unsigned on every installation
# in the field - and because the replacement key lived inside a Docker volume,
# nothing here would have looked wrong. The first symptom would have been
# customers' `apt update` failing.
#
# It also produced a flat repository layout (`deb https://HOST/ ./`) while the
# shipped sources.list asks for a suite layout (`.../repo trixie main`), so even
# correctly signed it would have 404'd.
#
# And it required Docker, which does not work on this machine at all - the
# Windows AF_UNIX bind fails with EACCES even elevated, which is why the whole
# build moved to WSL.
Write-Host "repo.ps1 is superseded and will not run." -ForegroundColor Red
Write-Host ""
Write-Host "It generated a SECOND repository signing key. Every shipped machine"
Write-Host "trusts 6CE37402BA0A0EF8 and rejects anything else as unsigned, so this"
Write-Host "would have broken 'apt update' for customers with no visible symptom here."
Write-Host ""
Write-Host "Use instead, from WSL:" -ForegroundColor Cyan
Write-Host "    sh packages/build-repo.sh"
Write-Host ""
Write-Host "Full release order is in docs/REPOSITORY.md - build first, publish second."
exit 1
