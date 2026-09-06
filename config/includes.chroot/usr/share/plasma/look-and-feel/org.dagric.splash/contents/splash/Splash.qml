// SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
// Obsidian Aperture. No network, audio, custom shader or artificial boot delay.
// Logo and text stay visible even when decorative motion is disabled.
import QtQuick
import QtCore
import "../../../../../dagric/design" as DagricDesign

Rectangle {
    id: root
    property int stage: 0
    // Read the same desktop setting as the first-run wrapper; never write it.
    property url motionSettingsUrl: "file://" + StandardPaths.writableLocation(StandardPaths.GenericConfigLocation) + "/kdeglobals"
    property real motionFactor: 1
    property bool reducedMotion: motionFactor <= 0
    Component.onCompleted: motionFactor = Number(motionPreferences.value("AnimationDurationFactor", 1))
    Settings {
        id: motionPreferences
        location: root.motionSettingsUrl
        category: "KDE"
    }
    property url logoSource: Qt.resolvedUrl("../../../../../icons/hicolor/scalable/apps/dagric-logo.svg")
    readonly property real progress: Math.max(0, Math.min(stage / 6.0, 1))
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#202024" }
        GradientStop { position: 1.0; color: "#101012" }
    }
    DagricDesign.Aperture {
        objectName: "startupAperture"
        width: root.width
        height: root.height
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -root.height * 0.03
        reducedMotion: root.reducedMotion
    }
    Column {
        id: identity
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -root.height * 0.09
        spacing: Math.max(12, Math.round(root.height * 0.025))
        Image {
            id: mark
            source: root.logoSource
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.max(64, Math.min(144, Math.round(root.height * 0.17)))
            height: width
            sourceSize.width: 512; sourceSize.height: 512
            fillMode: Image.PreserveAspectFit
            smooth: true
            visible: status === Image.Ready
        }
        Text {
            objectName: "startupWordmark"
            text: "DAGRIC"
            anchors.horizontalCenter: parent.horizontalCenter
            color: "#f5f5f7"
            font.pixelSize: Math.max(24, Math.min(52, Math.round(root.height * 0.052)))
            font.weight: Font.DemiBold
            font.letterSpacing: 8
        }
    }
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.max(identity.y + identity.height + 32, root.height * 0.85)
        spacing: 6
        Repeater {
            model: 6
            Rectangle {
                required property int index
                width: Math.max(18, Math.min(38, Math.round(root.width * 0.025)))
                height: 3; radius: 1.5
                color: root.stage > index ? "#b82036" : "#45454f"
                Behavior on color {
                    enabled: !root.reducedMotion
                    ColorAnimation { duration: 200 }
                }
            }
        }
        // Segments track actual Plasma stages, not an invented percent or timer.
    }
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: Math.max(20, root.height * 0.04)
        width: Math.min(360, parent.width * 0.4)
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 0.5; color: "#b82036" }
            GradientStop { position: 1; color: "transparent" }
        }
    }
}
