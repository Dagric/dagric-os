# Obsidian Aperture — startup and first-run redesign

Private candidate source: `b53adf2c99ec6664cc4cce113e00576f2a772c56`.
Visual implementation: `ce70344249066f44bae1370a94c3b7f516dc291f` plus the
packaging and narrow-screen corrections in the candidate commit.

## Design and implementation

- Shared native QML artwork: luminous red elliptical contours, soft charcoal
  depth and a 900 ms decorative reveal. No moving/zooming text, looping effects,
  shader package, network image, soundtrack or artificial startup delay.
- Existing official Dagric logo geometry and colors preserved; real SVG loading
  explicitly supported by `qt6-svg-plugins` instead of assuming the QtSvg library
  contains its image-format plugin.
- Startup has a centered vector mark, spaced wordmark, and six progress segments
  driven by Plasma startup stages. It reads AnimationDurationFactor from the
  user's KDE configuration, without writing it, and disables motion at zero.
- Welcome has a responsive editorial layout and a separate decorative brand
  panel on wide screens. Small screens retain the functional content.
- Step rail highlights the current step; the header progress line and card
  feedback use brief transitions with the existing reduced-motion preference.
- Very narrow layouts use smaller button padding. During a text-size trial,
  short windows hide the inactive size choices so Keep/Put back stay reachable.
- Shared artwork is part of dagric-branding; wizard remains in dagric-tools.
  Branding declares the SVG and QtCore runtime dependencies explicitly.
- Settings preview is rendered from the actual startup QML, not a separately
  drawn approximation. The renderer needs Qt 6 Quick Test in the build environment.

## Plugin use

Adobe's connected typography tool was consulted. It suggested Source Sans 3
among other fonts. No Adobe font files or third-party generated artwork were
downloaded or redistributed. The shipped desktop font preference is retained.
Artwork and animation are implemented in native QML. The Dagric lab plugin is
used for isolated image boot verification; this is not an Express animation.

## Verified before image completion

- 17 Qt checks pass: Free/Pro 800x600, 1366x768, 1920x1080; light mode;
  150% text; 360x400; trial navigation; step progress; actual reduced-motion INI
  read; finite decorative animation; and a pixel comparison showing no motion
  after the preference is enabled.
- Boot presentation and source flow/contrast checks pass.
- The 400x225 Settings preview and large/small rendered layouts were inspected.
- An earlier build at ce70344 was intentionally stopped in its isolated process
  group after packaging/narrow-screen corrections. Its directory was preserved;
  it must not be distributed as the finished candidate.

## Image verification

The full source-only developer audit passed on an isolated checkout of b53adf2.
The final private build in `/var/tmp/dagric-private-pro.8TcOFt` failed while
installing packages: Windows C: reached zero free bytes, and the WSL filesystem
became read-only with I/O errors. No finished new ISO or live acceptance is
claimed. The previous downloads and running guest do not contain this redesign.

One superseded Windows ISO was copied to
`D:/Dagric-build-archive/20260905-startup-refined/dagric-os-pro-1.0-amd64.iso`,
checked against SHA-256
`af075a4926fb24c749e49812ca9583ce6e4d4e0ebe7c943f0821ca49e5795bfc`, then its
duplicate C: file was removed. Approximately 4.9 GB became free. The latest
metadata-cleaned download and all test disks, videos and business files were
left unchanged. The archived ISO is recoverable at the D: path above.

The next step is build-storage recovery, preferably relocating the Debian WSL
build environment to D: (about 682 GB available at the check). This affects the
whole Debian environment and requires restarting it, so it has not been done
without specific user direction. After recovery, rebuild b53adf2, run actual
image readback/metadata cleanup, verify the local copy and boot-test it.

This work does not establish installation/recovery acceptance, physical UEFI or
Secure Boot compatibility, firmware/artwork rights approval, full accessibility
certification, or public release readiness. No website/release publication or
GitHub push is part of this pass.
