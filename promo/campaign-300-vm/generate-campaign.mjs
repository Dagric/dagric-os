import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

const features = [
  { slug:"live-vs-installed", category:"First run", claim:"The first-run wizard changes its explanation between the live trial and an installed system.", evidence:"docs/FIELD-NOTES-2026-08-15.md — zram section, final paragraph", shots:["Boot the live ISO to the first-run screen","Record the live-trial wording","Cut to the installed-system wording"] },
  { slug:"appearance-auto-revert", category:"Appearance", claim:"Appearance previews are not kept until Keep is pressed, and an unconfirmed change reverts after twenty seconds.", evidence:"docs/EDITIONS.md — Dagric Appearance", shots:["Open Dagric Appearance","Apply a visibly different style","Let the undo countdown revert the preview"] },
  { slug:"styles-and-layouts", category:"Appearance", claim:"Free includes four styles and Pro includes seven; layouts change the arrangement without rebuilding the workspace.", evidence:"docs/EDITIONS.md — Dagric OS (free)", shots:["Open the Styles gallery","Show the Free and Pro labels without implying locked accessibility","Switch to the Layouts tab"] },
  { slug:"wallpaper-packs", category:"Appearance", claim:"Dagric ships thirty-four wallpaper packs, including fourteen logo-free Clean variants.", evidence:"docs/EDITIONS.md — Dagric OS (free)", shots:["Open the wallpaper grid","Move through branded and Clean pairs","Apply one preview and return to the original"] },
  { slug:"accessible-live-boot", category:"Accessibility", claim:"The live ISO includes a screen-reader boot entry directly under the default entry.", evidence:"docs/EDITIONS.md — Accessibility", shots:["Boot to the ISO menu","Highlight the screen-reader entry","Do not claim the SDDM login screen speaks"] },
  { slug:"screen-reader-shortcut", category:"Accessibility", claim:"Meta+Alt+S toggles the Orca screen reader in the desktop session.", evidence:"docs/EDITIONS.md — Accessibility", shots:["Open the Accessibility page","Show the Screen Reader launcher entry","Display the shortcut text without claiming an audio test"] },
  { slug:"high-contrast-style", category:"Accessibility", claim:"The High Contrast style is in Free and its measured color pairs pass a 7:1 build-time threshold.", evidence:"docs/EDITIONS.md — Accessibility", shots:["Open Styles","Preview High Contrast","Show representative text and desktop-icon contrast"] },
  { slug:"offline-help", category:"Documentation", claim:"Dagric includes an offline manual and guide that work without a network connection.", evidence:"docs/FIELD-NOTES-2026-08-15.md — What already works", shots:["Disconnect the VM network","Open the User Guide from the Hub","Search for a familiar Windows app name"] },
  { slug:"task-manager-shortcut", category:"Familiar controls", claim:"Ctrl+Shift+Esc opens the Task Manager; Ctrl+Esc is not advertised because Plasma 6 does not bind it.", evidence:"docs/EDITIONS.md — The first hour", shots:["Show the desktop","Press Ctrl+Shift+Esc","Record Task Manager opening"] },
  { slug:"wayland-x11-rescue", category:"Compatibility", claim:"Dagric offers Plasma Wayland and a functioning X11 rescue session for older graphics problems.", evidence:"docs/EDITIONS.md — Sessions", shots:["Open the SDDM session chooser","Show Wayland and X11 entries","Explain that display scaling helper behavior differs on X11"] },
  { slug:"snapshot-pairs", category:"Recovery", claim:"On the default Btrfs installation, apt transactions create a pre/post snapshot pair and GRUB exposes snapshot recovery.", evidence:"docs/TEST-REPORT.md — Snapshot recovery; docs/FIELD-NOTES-2026-08-15.md", shots:["Open a terminal only inside the VM capture session","Show the snapshot list after an update","Reboot to the GRUB snapshot submenu without performing a destructive rollback"] },
  { slug:"software-store-install", category:"Daily use", claim:"Installing an application from the Software Store was verified end to end, including the authorization prompt.", evidence:"docs/FIELD-NOTES-2026-08-15.md — What already works", shots:["Open Discover","Choose a small test application","Stop before or safely complete installation in the disposable VM"] },
  { slug:"printing-and-scanning", category:"Hardware", claim:"Both editions include CUPS, PDF printing, broad printer filters, scanning tools, and IPP-over-USB support.", evidence:"docs/TEST-REPORT.md — Gap analysis; docs/FIELD-NOTES-2026-08-15.md", shots:["Open printer settings","Show the PDF queue","Open the scanner app and state that real-device validation is still needed"] },
  { slug:"firmware-updates", category:"Maintenance", claim:"Fwupd is included so supported device firmware can appear through the Software Store.", evidence:"docs/TEST-REPORT.md — Gap analysis", shots:["Open Discover updates","Show the firmware area if the VM exposes it","State that availability depends on the actual hardware vendor"] },
  { slug:"vpn-import", category:"Networking", claim:"OpenVPN and OpenConnect import support is included in both editions.", evidence:"docs/TEST-REPORT.md — Gap analysis", shots:["Open Network settings","Open Add Connection","Show the VPN import choices without entering credentials"] },
  { slug:"media-codecs", category:"Media", claim:"Both editions include a broad GStreamer/libav codec set; the measured test image reported 269 plugins.", evidence:"docs/FIELD-NOTES-2026-08-15.md — What already works", shots:["Open a Dagric-owned sample video","Show playback controls","Use the measured plugin count only with its test-date context"] },
  { slug:"office-font-fidelity", category:"Documents", claim:"LibreOffice ships with metric-compatible fonts intended to reduce layout shifts in common Office documents.", evidence:"docs/TEST-REPORT.md — Gap analysis; docs/FIELD-NOTES-2026-08-15.md", shots:["Open Writer","Show the installed Carlito and Caladea families","Avoid claiming perfect document fidelity"] },
  { slug:"fingerprint-and-thermal", category:"Laptop support", claim:"Fingerprint login components and thermald are included for supported laptops.", evidence:"docs/TEST-REPORT.md — Gap analysis", shots:["Open user or authentication settings","Show the fingerprint option only if exposed by the VM","Use an on-screen note that hardware support varies"] },
  { slug:"zram-measurement", category:"Performance", claim:"One measured 3 GB test system compressed 433 MB of pages into 51 MB of RAM using zstd zram.", evidence:"docs/FIELD-NOTES-2026-08-15.md — zram", shots:["Record the Memory view","Show the zram measurement source","Label this as one measured system, not a universal result"] },
  { slug:"idle-memory-measurement", category:"Performance", claim:"A measured installed Plasma session used about 642 MB PSS after subtracting the demo harness.", evidence:"docs/FIELD-NOTES-2026-08-15.md — memory number", shots:["Open Task Manager","Show the quiet desktop","Overlay the PSS methodology and test context"] },
  { slug:"iso-to-usb-writer", category:"Installation", claim:"Double-clicking an ISO now opens the USB Writer path instead of failing silently.", evidence:"docs/FIELD-NOTES-2026-08-15.md — Fixed this session", shots:["Open Files to a copied test ISO","Double-click the ISO","Record USB Writer opening; do not select a real drive"] },
  { slug:"phone-integration", category:"Phone", claim:"KDE Connect is included for phone integration, and Bluetooth file transfer remains available without pulling in an unrelated GNOME contacts stack.", evidence:"docs/FIELD-NOTES-2026-08-15.md — Bluetooth correction", shots:["Open KDE Connect","Show the pairing screen","State that a real phone is required for end-to-end verification"] },
  { slug:"image-formats", category:"Daily use", claim:"WebP and TIFF image support was verified on both editions.", evidence:"docs/FIELD-NOTES-2026-08-15.md — What already works", shots:["Open Files to Dagric-owned WebP and TIFF samples","Open each in the image viewer","Avoid implying support for every image codec"] },
  { slug:"apparmor-firewall", category:"Security", claim:"Free includes AppArmor, firewalld, hardened kernel settings, silent security updates, and an on-demand Lynis check.", evidence:"docs/EDITIONS.md — Security baseline", shots:["Open Security Checkup","Show firewall status","Keep the apparmor-profiles complain-mode qualification in the caption"] },
  { slug:"opensnitch-monitor", category:"Pro security", claim:"Pro includes OpenSnitch in monitor mode; outbound blocking is opt-in from its interface.", evidence:"docs/EDITIONS.md — Security Suite", shots:["Open OpenSnitch","Show monitor mode","Do not enable blocking during the marketing capture"] },
  { slug:"usbguard-consent", category:"Pro security", claim:"The USB protection helper builds an allow-list from connected devices before enabling USBGuard.", evidence:"docs/EDITIONS.md — Security Suite", shots:["Open the USB Protection helper","Record the explanation and consent screen","Do not arm USBGuard in the capture VM unless input recovery is guaranteed"] },
  { slug:"creator-suite", category:"Pro creators", claim:"Pro includes GIMP, Krita, Inkscape, Blender, OBS Studio, Kdenlive, and other creator tools.", evidence:"docs/TEST-REPORT.md — verified binaries; docs/EDITIONS.md — Creator suite", shots:["Open the creator-app section of the launcher","Launch two or three apps one at a time","Use only Dagric-owned sample media"] },
  { slug:"windows-and-gaming-helpers", category:"Compatibility", claim:"Dagric provides consent-based helpers for Bottles, Steam, Heroic, ProtonUp-Qt, and a full Windows VM path; compatibility still depends on each app or game.", evidence:"docs/EDITIONS.md — Owner-consent helpers", shots:["Open Hub → Add more apps","Show the helpers without downloading third-party payloads","End on the compatibility qualification"] },
  { slug:"developer-stack", category:"Pro developers", claim:"Pro includes Docker, Podman, Distrobox, Git, Python tooling, and an SSH server that stays off until enabled.", evidence:"docs/EDITIONS.md — Developer toolchain", shots:["Open the developer section","Show installed tool entries or version screens","Emphasize that SSH server is off by default"] },
  { slug:"backup-stack", category:"Pro backup", claim:"Pro includes Borg, Vorta, and rclone for local encrypted backups and optional cloud destinations.", evidence:"docs/EDITIONS.md — Creator suite", shots:["Open Vorta","Create no real backup destination","Show that cloud access is optional and requires the owner’s credentials"] },
];

const formats = [
  { id:"human-question", label:"Human question", duration:18, dialogue:(f)=>`You might be wondering, “${f.claim}” Let’s look at the actual screen and the limitation that goes with it.` },
  { id:"screen-first", label:"Screen first", duration:14, dialogue:(f)=>`Here it is on a running Dagric system: ${f.claim}` },
  { id:"three-beats", label:"Three-beat explainer", duration:24, dialogue:(f)=>`Three quick beats: what it is, where it lives, and what you should verify yourself. ${f.claim}` },
  { id:"owner-scenario", label:"Owner scenario", duration:30, dialogue:(f)=>`Imagine this is the PC you already use. ${f.claim} Here is the cautious way to try it.` },
  { id:"myth-check", label:"Myth check", duration:20, dialogue:(f)=>`This is not a promise that every machine behaves the same. What Dagric actually documents is: ${f.claim}` },
  { id:"quiet-demo", label:"Quiet demo", duration:12, dialogue:(f)=>`Watch the workflow. ${f.claim}` },
  { id:"proof-card", label:"Proof card", duration:16, dialogue:(f)=>`${f.claim} The evidence path is included below so you can check it.` },
  { id:"before-you-install", label:"Before you install", duration:27, dialogue:(f)=>`Before you install anything, this is worth checking on your own hardware: ${f.claim}` },
  { id:"honest-limitation", label:"Honest limitation", duration:22, dialogue:(f)=>`The useful feature is real, and so is the boundary. ${f.claim} We will show both.` },
  { id:"founder-voice", label:"Founder-style voice", duration:36, dialogue:(f)=>`We built this for people who want to understand what their computer is doing. ${f.claim} Here is the real interface, not a mockup.` },
];

const platforms = ["TikTok", "Instagram Reels", "YouTube Shorts", "Snapchat Spotlight"];
const items = [];

for (const feature of features) {
  for (const format of formats) {
    const number = items.length + 1;
    const platform = platforms[(number - 1) % platforms.length];
    const title = `${feature.category}: ${format.label} — ${feature.slug.replaceAll("-", " ")}`;
    const hook = format.dialogue(feature).split(/(?<=[.!?])\s/)[0];
    const dialogue = format.dialogue(feature);
    const caption = `${format.label}: ${feature.claim} Evidence: ${feature.evidence}. See Dagric OS: https://dagric.com #DagricOS #Linux`;
    items.push({
      id:`DGR-VM-${String(number).padStart(3,"0")}`,
      slug:`${feature.slug}-${format.id}`,
      status:"SCRIPTED_WAITING_FOR_VM_FOOTAGE",
      category:feature.category,
      format:format.label,
      durationSeconds:format.duration,
      platform,
      title,
      hook,
      dialogue,
      caption,
      evidence:feature.evidence,
      vmShots:feature.shots,
      visualStyle:number % 3 === 0 ? "cursor-led real-time demo" : number % 3 === 1 ? "tight UI details with human voiceover" : "screen recording with short face-free founder narration",
      audioRule:"Original narration or silence only. No downloaded music; platform-cleared commercial audio may be added at publish time.",
      claimRule:"Show the real VM screen and preserve every qualification. Do not universalize measured results or imply third-party endorsement.",
      outputSpec:"Record 16:9 source at 1920x1080; compose a separate native 9:16 edit for vertical platforms rather than stretching or adding bars.",
    });
  }
}

const unique = (key) => new Set(items.map((item) => item[key])).size;
if (items.length !== 300 || unique("slug") !== 300 || unique("title") !== 300 || unique("caption") !== 300) {
  throw new Error(`Uniqueness failed: count=${items.length}, slugs=${unique("slug")}, titles=${unique("title")}, captions=${unique("caption")}`);
}

fs.mkdirSync(here,{recursive:true});
fs.writeFileSync(path.join(here,"campaign.json"),`${JSON.stringify({generatedAt:new Date().toISOString(),count:items.length,features:features.length,formats:formats.length,items},null,2)}\n`);

const cols=["id","status","slug","platform","durationSeconds","title","hook","dialogue","evidence"];
const csv=[cols.join(","),...items.map(item=>cols.map(col=>`"${String(item[col]).replaceAll('"','""')}"`).join(","))].join("\n");
fs.writeFileSync(path.join(here,"production-ledger.csv"),`${csv}\n`);

const captureRows=[];
for(const feature of features){
  feature.shots.forEach((shot,index)=>captureRows.push({feature:feature.slug,shot:index+1,instruction:shot,evidence:feature.evidence}));
}
const captureCols=["feature","shot","instruction","evidence"];
const captureCsv=[captureCols.join(","),...captureRows.map(row=>captureCols.map(col=>`"${String(row[col]).replaceAll('"','""')}"`).join(","))].join("\n");
fs.writeFileSync(path.join(here,"vm-capture-plan.csv"),`${captureCsv}\n`);

const readme=`# Dagric VM-recorded 300-video campaign\n\nThis is a production ledger for 300 distinct, evidence-backed video concepts: 30 verified product areas × 10 human presentation formats. It is not a folder of finished videos. Every row stays \`SCRIPTED_WAITING_FOR_VM_FOOTAGE\` until real Dagric VM footage is recorded, edited, listened to, and audited.\n\n## Production rules\n\n- Use the newest tested Dagric ISO and record the actual VM interface.\n- Record clean 1920×1080 source footage, then make a separate native vertical composition; do not stretch 16:9 into 9:16.\n- Keep measured results tied to their test context. Hardware, firmware, app, and game compatibility must never be universalized.\n- Do not show passwords, account details, private files, host notifications, or unrelated browser tabs.\n- Use Dagric-owned media and original narration. No downloaded music.\n- Do not publish any item while its status says \`SCRIPTED_WAITING_FOR_VM_FOOTAGE\`.\n- Adobe processing is handled in reviewed batches of at most 20 files.\n\n## Files\n\n- \`campaign.json\` — dialogue, captions, evidence, shot lists, and platform targets.\n- \`production-ledger.csv\` — compact production tracking sheet.\n- \`vm-capture-plan.csv\` — 90 concrete VM shots grouped into 30 reusable source sequences.\n`;
fs.writeFileSync(path.join(here,"README.md"),readme);

console.log(JSON.stringify({count:items.length,features:features.length,formats:formats.length,uniqueSlugs:unique("slug"),uniqueTitles:unique("title"),uniqueCaptions:unique("caption"),captureShots:captureRows.length},null,2));
