// Dagric OS — the Plasma startup screen.
//
// This window covers the ~16 seconds between signing in and the desktop
// appearing. Until this file existed that stretch was KDE's stock Breeze
// splash — the last unbranded surface in the whole boot, sitting right after
// a branded boot menu, a branded Plymouth splash and a branded login screen.
//
// DESIGN CONTRACT, same as the Plymouth theme's:
//   * The background paints unconditionally — a solid gradient with no asset,
//     network or font dependency, in the exact colours Plymouth uses
//     (#0e1826 -> #050810), so Plymouth, SDDM and this screen read as one
//     continuous surface instead of three products taking turns.
//   * The wordmark is an Image with a Text fallback wired to Image.status —
//     if the PNG is missing or unreadable, the brand name renders as type
//     rather than as a hole.
//   * Everything animated is ADDITIVE and starts invisible. The failure mode
//     of any animation here is "static splash", never "no splash".
//
// And the failure mode of this whole FILE is mild by construction: if the QML
// does not parse, ksplashqml exits and the session simply continues with no
// splash. That is unlike Plymouth, where a broken script can black out the
// boot — which is why this screen gets richer animation than the boot splash
// was ever allowed.
//
// `stage` arrives from startplasma: 1..5 as kcminit / ksmserver / the window
// manager / the shell come up, 6 when the desktop is ready. The progress
// hairline maps it directly; nothing here invents fake progress.
import QtQuick

// No anchors and no size on the root item, deliberately: ksplashqml sizes the
// root to its window (Breeze's own Splash.qml relies on the same), and a root
// that anchors to a parent it does not own is a runtime error waiting on a Qt
// version to decide to enforce it.
Rectangle {
    id: root
    property int stage: 0

    gradient: Gradient {
        GradientStop { position: 0.0; color: "#0e1826" }
        GradientStop { position: 1.0; color: "#050810" }
    }

    onStageChanged: {
        if (stage >= 1 && content.opacity < 1 && !entrance.running)
            entrance.running = true;
        if (stage >= 2 && !sweep.done && !sweepRun.running)
            sweepRun.running = true;
    }

    Item {
        id: content
        anchors.fill: parent
        opacity: 0

        // Wordmark block, centred slightly above the middle — the same
        // optical position the Plymouth art uses, so the handoff between the
        // two screens does not appear to move the logo.
        Item {
            id: lockup
            width: mark.visible ? mark.width : fallback.width
            height: (mark.visible ? mark.height : fallback.height) + 26
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: -Math.round(parent.height * 0.06)

            // THE SVG, NOT THE PNG, and that is the whole point of this block.
            //
            // This pointed at dagric-logo.png with sourceSize 512 — but that
            // PNG is 256x256 (read from its IHDR), and sourceSize is a DECODE
            // CEILING, never an upscaler. Qt requests sourceSize * the device
            // pixel ratio, so at 150% scaling the mark is asked to fill 330
            // device pixels and at 200% it is 440, from 256 pixels of source.
            // The sourceSize lines were a no-op and the wordmark rendered soft
            // on exactly the HiDPI laptops this OS is sold to rescue.
            //
            // The vector is already on the image — the hicolor icon theme ships
            // it — so this costs no new asset and no rasteriser at build time.
            // With an SVG source, sourceSize stops being a ceiling and becomes
            // the render size: QtSvg rasterises at whatever is asked for, so
            // the mark is sharp at any scaling factor.
            //
            // libqt6svg6 is confirmed present (it appears as "Setting up
            // libqt6svg6:amd64" in out/free-rebuild.log), which is what supplies
            // the qsvg image-format plugin QML's Image needs to load this at
            // all. If that ever stops being true the Text fallback below takes
            // over on its own — status simply never reaches Ready — so the
            // failure mode is the brand set in type, not an empty screen.
            Image {
                id: mark
                source: "file:///usr/share/icons/hicolor/scalable/apps/dagric-logo.svg"
                width: Math.min(220, Math.round(root.width * 0.18))
                height: width
                sourceSize.width: 512
                sourceSize.height: 512
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: status === Image.Ready
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // The fallback is the brand set in plain type. It exists so a
            // missing or corrupt logo file degrades to something an owner
            // would never recognise as broken.
            Text {
                id: fallback
                visible: mark.status !== Image.Ready
                text: "Dagric OS"
                color: "#e7eef7"
                font.pixelSize: Math.min(64, Math.round(root.width * 0.05))
                font.weight: Font.Light
                font.letterSpacing: 2
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // The light sweep: one soft highlight travelling across the
            // wordmark, once, then never again — the same restraint rule as
            // the Plymouth sweep, because this screen is shown to somebody
            // waiting and a looping shimmer makes waiting feel longer.
            Rectangle {
                id: sweep
                property bool done: false
                width: 36
                height: lockup.height * 1.6
                rotation: 14
                opacity: 0
                x: -width
                y: -lockup.height * 0.3
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.5; color: "#28ffffff" }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }
        }

        // The progress hairline: honest, driven only by `stage`. Its track is
        // barely-there; the fill is the accent the rest of the brand uses.
        Rectangle {
            id: track
            width: Math.min(300, Math.round(root.width * 0.24))
            height: 2
            radius: 1
            color: "#1c2b40"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: lockup.bottom
            anchors.topMargin: 34

            Rectangle {
                id: fill
                height: parent.height
                radius: 1
                color: "#3fa9f5"
                width: Math.round(track.width * Math.min(root.stage / 6.0, 1.0))
                Behavior on width {
                    NumberAnimation { duration: 350; easing.type: Easing.OutCubic }
                }
            }
        }
    }

    // The entrance: the lockup resolves into place over ~0.7 s — an eased
    // curve, not a linear ramp, for the same reason the Plymouth commit gives:
    // linear opacity reads as a dimmer being turned up, an eased curve reads
    // as something coming into focus.
    NumberAnimation {
        id: entrance
        target: content
        property: "opacity"
        from: 0; to: 1
        duration: 700
        easing.type: Easing.OutCubic
    }

    SequentialAnimation {
        id: sweepRun
        // Let the entrance finish before the flourish starts.
        PauseAnimation { duration: 500 }
        ScriptAction { script: sweep.opacity = 1 }
        NumberAnimation {
            target: sweep
            property: "x"
            from: -sweep.width
            to: lockup.width + sweep.width
            duration: 900
            easing.type: Easing.InOutQuad
        }
        ScriptAction { script: { sweep.opacity = 0; sweep.done = true; } }
    }
}
