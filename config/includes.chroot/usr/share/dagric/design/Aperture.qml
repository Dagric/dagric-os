// SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
// Original native artwork. Static curves repaint only for size/palette changes;
// scene-graph transforms move the decoration, never text or controls.
import QtQuick

Item {
    id: art
    property color accent: "#b82036"
    property bool dark: true
    property bool reducedMotion: false
    property bool animate: true
    property bool ambient: false
    property real drift: 0
    property real reveal: 1
    readonly property bool moving: intro.running || breathe.running
    Accessible.ignored: true
    clip: true

    function enter() {
        if (animate && !reducedMotion && visible) intro.restart();
    }
    Component.onCompleted: enter()
    onVisibleChanged: { if (visible) enter(); }
    onReducedMotionChanged: {
        if (reducedMotion) { intro.stop(); reveal = 1; }
    }
    onAnimateChanged: {
        if (!animate) { intro.stop(); reveal = 1; }
    }
    NumberAnimation {
        id: intro
        target: art; property: "reveal"
        from: 0; to: 1; duration: 900
        easing.type: Easing.OutCubic
    }
    SequentialAnimation {
        id: breathe
        running: art.ambient && art.animate && !art.reducedMotion && art.visible
        loops: Animation.Infinite
        NumberAnimation { target: art; property: "drift"; from: 0; to: 1; duration: 2200; easing.type: Easing.InOutSine }
        NumberAnimation { target: art; property: "drift"; from: 1; to: 0; duration: 2200; easing.type: Easing.InOutSine }
        onStopped: art.drift = 0
    }

    Item {
        anchors.fill: parent
        opacity: (0.65 + art.reveal * 0.35) * (1 - art.drift * 0.13)
        // Decor only: no blur/zoom on text and no per-frame Canvas repaint.
        rotation: -3 + art.reveal * 3 + art.drift * 2.5
        Canvas {
            id: contours
            anchors.fill: parent
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            Connections {
                target: art
                function onAccentChanged() { contours.requestPaint(); }
                function onDarkChanged() { contours.requestPaint(); }
            }
            onPaint: {
                var c = getContext("2d");
                c.reset();
                var w = width, h = height, size = Math.min(w, h);
                if (size <= 0) return;
                var cx = w * 0.52, cy = h * 0.48;
                var glow = c.createRadialGradient(cx, cy, size * 0.12, cx, cy, size * 0.48);
                glow.addColorStop(0, "transparent");
                glow.addColorStop(0.44, Qt.rgba(art.accent.r, art.accent.g, art.accent.b, art.dark ? 0.23 : 0.10));
                glow.addColorStop(1, "transparent");
                c.fillStyle = glow; c.fillRect(0, 0, w, h);
                c.save(); c.translate(cx, cy); c.rotate(-0.42);
                c.scale(1, 0.76);
                for (var i = 0; i < 7; i++) {
                    var radius = size * (0.24 + i * 0.039);
                    c.beginPath(); c.arc(0, 0, radius, -2.5, 2.55);
                    c.strokeStyle = Qt.rgba(art.accent.r, art.accent.g, art.accent.b, 0.10 + i * 0.055);
                    c.lineWidth = i === 5 ? 2 : 1; c.stroke();
                }
                var line = c.createLinearGradient(-size/2, 0, size/2, 0);
                line.addColorStop(0, "transparent");
                line.addColorStop(0.55, art.dark ? "#ffc3cb" : "#93162b");
                line.addColorStop(1, art.accent);
                c.beginPath(); c.arc(0, 0, size * 0.435, -2.35, 0.2);
                c.strokeStyle = line; c.lineWidth = 2; c.stroke();
                c.restore();
                // Small registration marks lend precision without visual noise.
                c.strokeStyle = art.dark ? "#45454f" : "#c2c2cc";
                c.lineWidth = 1;
                for (var j = 0; j < 4; j++) {
                    var x = w * (j % 2 ? 0.85 : 0.15), y = h * (j < 2 ? 0.18 : 0.82);
                    c.beginPath(); c.moveTo(x - 4, y); c.lineTo(x + 4, y);
                    c.moveTo(x, y - 4); c.lineTo(x, y + 4); c.stroke();
                }
            }
        }
    }
}
