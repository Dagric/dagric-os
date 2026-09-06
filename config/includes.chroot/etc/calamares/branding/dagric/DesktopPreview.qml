// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
Rectangle {
    id: preview
    property bool light: false
    property bool familiar: false
    property bool reducedMotion: false
    property int textPercent: 100
    property string assetBase: "file:///usr/share"
    property string wallpaperName: "DagricObsidianPulse"
    property string iconTheme: "DagricModern"
    color: light ? "#e1e5ed" : "#191c24"; radius: 12; clip: true
    Accessible.role: Accessible.StaticText
    Accessible.name: qsTr("Desktop preview. %1 appearance, %2 taskbar, application text %3%.").arg(light ? qsTr("Light") : qsTr("Dark")).arg(familiar ? qsTr("Familiar") : qsTr("Centered")).arg(textPercent)
    Image { anchors.fill: parent; source: preview.assetBase + "/wallpapers/" + preview.wallpaperName + "/contents/images/1920x1080.png"; fillMode: Image.PreserveAspectCrop }
    Rectangle {
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 10
        height: parent.height - 54; radius: 10; color: preview.light ? "#f1f3f7" : "#191c24"
        Behavior on color { ColorAnimation { duration: preview.reducedMotion ? 0 : 180 } }
        Text {
            anchors.fill: parent; anchors.margins: 8; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
            text: qsTr("Your files, your apps, your space."); wrapMode: Text.WordWrap
            font.pointSize: 10 * preview.textPercent / 100; color: preview.light ? "#171923" : "#f5f7fa"
        }
    }
    Rectangle {
        height: 30; anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8
        radius: 8; color: preview.light ? "#e1e5ed" : "#303440"
        Image { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; width: 22; height: 22; source: Qt.resolvedUrl("logo.png"); fillMode: Image.PreserveAspectFit }
        Row {
            x: preview.familiar ? 45 : Math.max(45, (parent.width - width) / 2); anchors.verticalCenter: parent.verticalCenter; spacing: 7
            Repeater { model: ["dagric-hub", "dagric-appearance", "dagric-display"]; Image { required property string modelData; width: 22; height: 22; source: preview.assetBase + "/icons/" + preview.iconTheme + "/32x32/apps/" + modelData + ".png"; fillMode: Image.PreserveAspectFit } }
        }
        Text { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: "12:00"; font.pointSize: 8; color: preview.light ? "#171923" : "#f5f7fa" }
    }
}
