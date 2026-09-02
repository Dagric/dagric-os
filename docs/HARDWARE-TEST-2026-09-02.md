# Physical-host hardware test — 2 September 2026

## Result

**CONDITIONAL FAIL — do not use the attached Seagate BUP Slim as release media,
an installation target, or the only copy of any data.** The processor and memory
smoke stress, both internal NVMe devices, Windows graphics diagnostics, present
device status, release-ISO reads, and final-ISO driver payload checks passed. The
external Seagate disk repeatedly failed reads at logical block zero and was no
longer exposed by the Windows storage stack as an online disk.

This was a non-destructive test of the physical PC while Windows was running. It
was **not** a native Dagric live boot or installation. Native Radeon acceleration,
Wi-Fi association, Bluetooth traffic, audible sound, suspend/resume, and physical
Secure Boot therefore remain unproved.

No serial number, MAC address, IP address, Windows user name, or storage content
was recorded.

## Machine under test

| Area | Detected hardware or state |
| --- | --- |
| Platform | MSI MS-7E71 desktop; American Megatrends firmware 1.A62 dated 24 June 2026 |
| Processor | AMD Ryzen 7 7700X; 8 cores / 16 logical processors; firmware virtualization enabled |
| Memory | 32 GB installed as two 16 GB DDR5 modules; configured at 4800 MT/s |
| Discrete graphics | AMD Radeon RX 9070 XT (`1002:7550`) |
| Integrated graphics | AMD Radeon Graphics (`1002:164e`) |
| Internal storage | T-FORCE TM8FFE001T NVMe and Crucial CT1000P310SSD8 NVMe |
| External storage | Seagate BUP Slim 2 TB USB disk — **failed this test** |
| Ethernet | Realtek PCIe 5GbE (`10ec:8126`), connected at 1 Gbit/s |
| Wi-Fi | MediaTek RZ616 Wi-Fi 6E (`14c3:0616`), detected but disconnected |
| Bluetooth | MediaTek RZ616 USB Bluetooth (`0e8d:0616`), detected |
| Audio | AMD/Realtek HDA plus USB audio devices, detected |
| TPM | AMD TPM 2.0, initialized and ready |
| Secure Boot | Disabled in the physical machine's firmware state |

## Tests performed now

| Test | Evidence | Result |
| --- | --- | --- |
| Present-device health | Every currently present Plug-and-Play device reported `OK`; historical phantom devices were excluded | Pass |
| Memory smoke test | Allocated and filled 512 MiB with deterministic per-block patterns; two SHA-256 verification passes matched (`1fa75d4e...67424`) | Pass |
| CPU smoke stress | 12 WSL-visible workers continuously hashed 4 MiB buffers for 30 seconds; all workers completed, totaling 151,030 iterations | Pass, limited-duration |
| Release-image storage reads | Read the 2,256,076,800-byte Free ISO twice; both reads produced `ef02f18a982f82b0578abf264d97703b2db72c3725fef0835ef2ea6a2ddb504e` | Pass |
| Internal storage status | Both NVMe devices remained online, operational, and healthy | Pass |
| DirectX diagnostics | RX 9070 XT and integrated Radeon detected with WDDM 3.2; Display, Sound, and Input tabs reported no problems | Pass under Windows only |
| Hardware-error event check | No WHEA CPU/memory event was found; Windows Disk event 154 repeatedly reported a hardware error at logical block `0x0` on Disk 2 | **Fail: external disk** |

The first and second full ISO reads completed in 4.352 and 2.586 seconds
respectively (about 494 and 832 MiB/s). These are cache-sensitive smoke-test
figures, not storage benchmarks.

The CPU test was intentionally short and used the 12 processors exposed to WSL;
it is not a substitute for an overnight memory test, thermal soak, or all-core
native Linux stress test.

## Final ISO support match

The inspected Free candidate is
`out/release-848b0203/dagric-os-1.0-amd64.iso`, built from source commit
`848b0203b40c8988f94424342e8047a34c733c36`. The tested file hash matched the
signed release manifest.

| Host device | Evidence inside the final ISO | Preflight result |
| --- | --- | --- |
| RX 9070 XT | Linux 6.12.107 `amdgpu` module with AMD display-class aliases; DCN 4, GC 12, PSP 14, SDMA 7, and SMU 14 firmware families | Payload present; native display and acceleration still required |
| Realtek 5GbE | `r8169` module has exact PCI alias `10ec:8126` | Match |
| MediaTek RZ616 Wi-Fi | `mt7921e` has exact PCI alias `14c3:0616`; MT7922 Wi-Fi firmware is present | Match; association still required |
| MediaTek Bluetooth | `btusb`/`btmtk` are present with MediaTek and standard Bluetooth USB aliases; MT7922 Bluetooth firmware is present | Match; traffic still required |
| NVMe storage | Linux NVMe host module is present | Payload present; both controllers need native enumeration |

Presence of a driver or firmware file is necessary but does not prove that a
device works on this machine. Only a physical Dagric boot can close that gap.

## Required response to the failed disk

1. Do not write a Dagric image to the Seagate disk and do not select it in the
   installer.
2. If it contains the only copy of important files, stop repeatedly accessing it
   and arrange a backup or recovery copy before diagnostics that write data.
3. Power the disk down, reconnect it directly with a known-good USB cable and a
   different motherboard port, then repeat a read-only health and event-log
   check.
4. If block-zero errors return, treat the disk or its USB bridge/cable as failed
   and remove it from release testing.

The internal NVMe disks did not exhibit this failure. No repair, formatting, or
write test was attempted on any drive.

### Remediation attempt

After the initial test, the Seagate USB device was still present in Plug-and-Play
with status `OK`, but Windows exposed no corresponding `Get-Disk` object, no
partition, and no mounted volume. A targeted device restart and hardware rescan
were attempted. Windows denied both operations because the diagnostic session
was not elevated. The device remained unavailable and another Disk event 154 was
recorded at 16:54.

This does not clear the failure. Plug-and-Play `OK` only means that Windows can
see the USB device; it does not override the storage stack's repeated inability
to read logical block zero. With no accessible disk or volume, there is no safe
filesystem repair to run. The next valid diagnostic step is the physical
cable/port isolation described above, followed by a new read-only check.

## Native Dagric test still required

1. Isolate or disconnect the failing Seagate disk.
2. Verify and write the Free ISO to a separate disposable USB flash drive.
3. Boot a non-installing Dagric live session with Secure Boot off.
4. Run **Check This PC**, confirm RX 9070 XT acceleration and native resolution,
   then test Ethernet, RZ616 Wi-Fi, Bluetooth, camera, audio input/output, both
   NVMe controllers, and suspend/resume.
5. Enable Secure Boot and repeat the physical live boot.
6. Only after those checks pass, test installation and recovery on a disposable
   or fully backed-up target.

Until those steps pass, this machine contributes a successful Windows-side
preflight and a failed external-storage finding—not a successful physical Dagric
qualification.
