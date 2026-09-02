# Hardware preflight — 30 August 2026

> A later physical-host smoke test found repeated hardware I/O errors on the
> external Seagate disk. Use the newer
> [2 September hardware test](HARDWARE-TEST-2026-09-02.md) as the current result.

## Result

**Ready for a live-USB trial; physical compatibility is not yet proven.** This
is a read-only inventory of the Windows host and a match against the kernel,
firmware, and userspace shipped in the signed Dagric OS 1.0 image. The machine
was not rebooted, no removable USB disk was attached, and Dagric did not run on
the physical hardware. This record must not be described as a successful
physical boot or install.

No serial number, MAC address, Windows user name, IP address, or storage content
was collected.

## Host and shipped support

| Component | Detected hardware | Evidence in the released image | Preflight |
| --- | --- | --- | --- |
| Platform | MSI MS-7E71 desktop, UEFI firmware | The ISO contains UEFI and legacy-BIOS boot paths | Ready to try |
| Secure Boot | Disabled in Windows firmware state | The image's shim/GRUB chain passed the virtual Secure Boot release gate | Not physically tested |
| Processor | AMD Ryzen 7 7700X, 8 cores / 16 threads, 64-bit | Linux 6.12.107 amd64 | Expected to work |
| Memory | 30.9 GiB | Well above the published 4 GiB minimum | Pass |
| Graphics | AMD Radeon RX 9070 XT (`1002:7550`) plus Ryzen integrated graphics (`1002:164e`) | Linux 6.12.107, Mesa 25.0.7, and `firmware-amd-graphics` 20250410-2; the firmware package contains GC 12 and DCN 4 files | Highest-risk item; live display and acceleration still need testing |
| Ethernet | Realtek 5GbE (`10ec:8126`) | Linux 6.12's `r8169` driver lists PCI ID `8126`; `firmware-realtek` includes `rtl8126a-2.fw` and `rtl8126a-3.fw` | Driver and firmware present |
| Wi-Fi | MediaTek RZ616 Wi-Fi 6E (`14c3:0616`) | Linux 6.12's `mt7921` PCI driver lists ID `0616`; `firmware-mediatek` includes MT7922 Wi-Fi and Bluetooth firmware | Driver and firmware present; association not tested |
| Storage | Two internal NVMe SSDs; external Seagate USB hard drive | Standard NVMe and USB-storage support is in the kernel | Detection expected; install target not tested |
| Camera | Logitech Brio 101 USB camera | Standard Linux USB-video stack ships | Not exercised |
| Audio | AMD/Realtek HDA and USB audio devices | PipeWire 1.4.2 and the Linux HDA/USB-audio drivers ship | Not exercised |
| Printer | No physical printer detected | CUPS 2.4.10 ships | No device to test |

The image package evidence comes from
[`site/manifest/dagric-os-1.0.packages`](../site/manifest/dagric-os-1.0.packages).
The device-ID checks can be reproduced against the upstream Linux 6.12
[`r8169`](https://github.com/torvalds/linux/blob/v6.12/drivers/net/ethernet/realtek/r8169_main.c)
and
[`mt7921`](https://github.com/torvalds/linux/blob/v6.12/drivers/net/wireless/mediatek/mt76/mt7921/pci.c)
drivers and Debian's Trixie file lists for
[`firmware-realtek`](https://packages.debian.org/trixie/all/firmware-realtek/filelist),
[`firmware-mediatek`](https://packages.debian.org/trixie/all/firmware-mediatek/filelist),
and
[`firmware-amd-graphics`](https://packages.debian.org/trixie/all/firmware-amd-graphics/filelist).

## Physical test still required

1. Attach an 8 GiB-or-larger USB drive whose contents may be erased.
2. Verify the Free ISO against the signed `SHA256SUMS`, then write it to that
   exact drive.
3. Boot the UEFI live session with Secure Boot off and run **Check This PC**.
4. Test the RX 9070 XT at the monitor's native resolution, Ethernet, RZ616
   Wi-Fi, Bluetooth, camera, every required audio device, suspend/resume, and
   access to each storage controller without installing.
5. Repeat the live boot with Secure Boot enabled.
6. Only after the live checks pass, install to a disposable or backed-up target
   and test boot, updates, snapshot rollback, and recovery.
