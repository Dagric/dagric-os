# Dagric Update

Dagric Update is the normal, in-place way to get the newest supported version
of Dagric and Debian packages. It updates the installed system; it is **not** a
reinstall and it does not create a new user account or move the person’s files.

Open **Dagric Update** from the application menu, or run:

```sh
sudo dagric-update
```

The menu action explains what will happen, requests administrator approval, and
then applies the update. `sudo dagric-update --check` only refreshes signed APT
metadata and displays the safe plan. It does not install packages.

## What it protects

- It receives packages only through APT, which validates Dagric's signed
  repository metadata and the Debian repositories. It does not fetch arbitrary
  package files or run a custom updater downloader.
- It uses `apt-get --with-new-pkgs upgrade`, not `full-upgrade`,
  `dist-upgrade`, or `autoremove`. New dependencies may be installed, but the
  normal updater never removes installed packages.
- It keeps the locally installed package configuration when a package supplies
  a new default, rather than overwriting an owner’s edited setting.
- It never copies, deletes, replaces, or migrates `/home`. The update’s scope is
  the installed package database and system files managed by APT.
- On a normal Dagric Btrfs install, it creates a clearly named Snapper checkpoint
  before package installation. A failed update can be rolled back from the GRUB
  Dagric snapshots entry. A machine without configured Btrfs/Snapper recovery
  requires an explicit second confirmation and should be backed up first.
- It downloads packages before changing installed packages, records a private
  root-owned report under `/var/lib/dagric/updates/`, and never runs automatic
  cleanup that could remove software or files.

## What it intentionally does not do

It does not move a system to a new Debian release. That operation changes APT
sources and can require package removals, so it remains the separately gated
`dagric-upgrade` process with its own preflight checks and rollback instructions.
If normal updates hold a package back because it needs a removal-capable or
release-level change, Dagric Update reports that rather than guessing.

## Releasing a new version to owners

For a customer to receive a new Dagric build, the new `.deb` packages must be
built, signed with the existing Dagric repository key, and published to the
configured HTTPS APT channel. Follow [REPOSITORY.md](REPOSITORY.md)'s release
checklist: bump the affected package versions, build and audit the ISO, build
the repository, verify signatures, then publish. The updater cannot make an
unpublished package available, and it deliberately does not bypass those
release controls.
