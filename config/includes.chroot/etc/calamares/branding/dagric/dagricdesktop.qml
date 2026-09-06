// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: page
    color: "#101218"
    property string mode: "dark"
    property string layout: "eleven"
    property string icons: "modern"
    property string textSize: "normal"
    property string wallpaper: "obsidian"
    property bool initialized: false
    property string assetBase: "file:///usr/share"
    readonly property string wallpaperName: ({obsidian:"DagricObsidianPulse", arctic:"DagricArcticClean", aurora:"DagricAurora"})[wallpaper] || "DagricObsidianPulse"
    readonly property string iconTheme: ({modern:"DagricModern", classic:"DagricClassic", "old-school":"DagricOldSchool"})[icons] || "DagricModern"
    readonly property var choiceIds: [["dark","light"], ["classic","eleven"], ["modern","classic","old-school"], ["normal","bigger","biggest"], ["obsidian","arctic","aurora"]]
    readonly property var choiceLabels: [["Dark","Light"], ["Familiar","Centered"], ["Modern icons","Classic icons","Old school icons"], ["100% text","125% text","150% text"], ["Obsidian","Arctic","Aurora"]]
    readonly property string profile: [mode, layout, icons, textSize, wallpaper].map(function(value, i) { return choiceLabels[i][choiceIds[i].indexOf(value)] }).join(" · ")
    readonly property int textPercent: textSize === "biggest" ? 150 : (textSize === "bigger" ? 125 : 100)
    function storeChoice() { if (initialized) config.packageChoice = profile }
    onProfileChanged: storeChoice()
    Component.onCompleted: {
        var old = String(config.packageChoice || "").split(" · ")
        if (old.length === 5 && old.every(function(value, i) { return choiceLabels[i].indexOf(value) >= 0 })) {
            var ids = old.map(function(value, i) { return choiceIds[i][choiceLabels[i].indexOf(value)] })
            mode = ids[0]; layout = ids[1]; icons = ids[2]; textSize = ids[3]; wallpaper = ids[4]
        }
        initialized = true; storeChoice()
    }
    ScrollView {
        id: scroll
        anchors.fill: parent; anchors.margins: 20
        clip: true
        contentWidth: Math.max(0, availableWidth - 16)
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn
        ColumnLayout {
            width: Math.max(0, scroll.availableWidth - 16)
            spacing: 14
            Text { text: qsTr("Make it feel like yours."); color: "#f5f7fa"; font.pixelSize: 27; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Text { text: qsTr("Choose once, here. Your account opens with these preferences after installation — no second setup wizard. You can change them later in Desktop & taskbar."); color: "#bfc4cf"; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 152; radius: 12
                color: page.mode === "dark" ? "#191c24" : "#edf0f5"
                border.color: "#59606e"
                Image { anchors.fill: parent; anchors.margins: 2; source: page.assetBase + "/wallpapers/" + page.wallpaperName + "/contents/images/1920x1080.png"; fillMode: Image.PreserveAspectCrop; clip: true }
                Rectangle {
                    anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 12
                    height: 85; radius: 10; color: page.mode === "dark" ? "#191c24" : "#edf0f5"
                    Text { anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 10; text: qsTr("Preview · application text %1%").arg(page.textPercent); color: page.mode === "dark" ? "#c2c8d2" : "#3f4653"; font.pixelSize: 12 }
                    Text { anchors.bottom: parent.bottom; anchors.bottomMargin: 10; anchors.horizontalCenter: parent.horizontalCenter; width: parent.width - 24; horizontalAlignment: Text.AlignHCenter; text: qsTr("Your files, your apps, your space."); wrapMode: Text.WordWrap; font.pixelSize: 16 * page.textPercent / 100; color: page.mode === "dark" ? "#ffffff" : "#151821" }
                }
                Rectangle {
                    height: 30; anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8; radius: 8; color: page.mode === "dark" ? "#303440" : "#d8dce5"
                    Image { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; width: 22; height: 22; source: Qt.resolvedUrl("logo.png"); fillMode: Image.PreserveAspectFit }
                    Row { x: page.layout === "classic" ? 45 : (parent.width - width) / 2; anchors.verticalCenter: parent.verticalCenter; spacing: 7
                        Repeater { model: ["dagric-hub", "dagric-appearance", "dagric-display"]; Image { required property string modelData; width: 22; height: 22; source: page.assetBase + "/icons/" + page.iconTheme + "/32x32/apps/" + modelData + ".png"; fillMode: Image.PreserveAspectFit } }
                    }
                    Text { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: "12:00"; font.pixelSize: 11; color: page.mode === "dark" ? "#f5f7fa" : "#151821" }
                }
            }
            Text { text: qsTr("Appearance"); color: "#f5f7fa"; font.pixelSize: 16; font.bold: true }
            Flow { Layout.fillWidth: true; spacing: 8
                ProfileChoice { text: qsTr("Dark"); detail: qsTr("Obsidian & graphite"); selected: page.mode === "dark"; onClicked: page.mode = "dark" }
                ProfileChoice { text: qsTr("Light"); detail: qsTr("Bright & clear"); selected: page.mode === "light"; onClicked: page.mode = "light" }
            }
            Text { text: qsTr("Taskbar"); color: "#f5f7fa"; font.pixelSize: 16; font.bold: true }
            Flow { Layout.fillWidth: true; spacing: 8
                ProfileChoice { text: qsTr("Familiar"); detail: qsTr("Apps on the left"); selected: page.layout === "classic"; onClicked: page.layout = "classic" }
                ProfileChoice { text: qsTr("Centered"); detail: qsTr("Apps in the middle"); selected: page.layout === "eleven"; onClicked: page.layout = "eleven" }
            }
            Text { text: qsTr("Application text"); color: "#f5f7fa"; font.pixelSize: 16; font.bold: true }
            Flow { Layout.fillWidth: true; spacing: 8
                ProfileChoice { text: qsTr("Normal · 100%"); detail: qsTr("Standard text"); selected: page.textSize === "normal"; onClicked: page.textSize = "normal" }
                ProfileChoice { text: qsTr("Bigger · 125%"); detail: qsTr("Easier to read"); selected: page.textSize === "bigger"; onClicked: page.textSize = "bigger" }
                ProfileChoice { text: qsTr("Biggest · 150%"); detail: qsTr("Large text"); selected: page.textSize === "biggest"; onClicked: page.textSize = "biggest" }
            }
            Text { text: qsTr("Icon style"); color: "#f5f7fa"; font.pixelSize: 16; font.bold: true }
            Flow { Layout.fillWidth: true; spacing: 8
                ProfileChoice { text: qsTr("Modern"); detail: qsTr("Dimensional"); selected: page.icons === "modern"; onClicked: page.icons = "modern" }
                ProfileChoice { text: qsTr("Classic"); detail: qsTr("Enamel badges"); selected: page.icons === "classic"; onClicked: page.icons = "classic" }
                ProfileChoice { text: qsTr("Old school"); detail: qsTr("Pixel-inspired"); selected: page.icons === "old-school"; onClicked: page.icons = "old-school" }
            }
            Text { text: qsTr("Background"); color: "#f5f7fa"; font.pixelSize: 16; font.bold: true }
            Flow { Layout.fillWidth: true; spacing: 8
                ProfileChoice { text: qsTr("Obsidian"); detail: qsTr("Red & black"); selected: page.wallpaper === "obsidian"; onClicked: page.wallpaper = "obsidian" }
                ProfileChoice { text: qsTr("Arctic"); detail: qsTr("Open & bright"); selected: page.wallpaper === "arctic"; onClicked: page.wallpaper = "arctic" }
                ProfileChoice { text: qsTr("Aurora"); detail: qsTr("Color & atmosphere"); selected: page.wallpaper === "aurora"; onClicked: page.wallpaper = "aurora" }
            }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: qsTr("These choices do not resize partitions, change accounts, or install extra apps. Display scaling follows your screen; the text preview changes application fonts."); color: "#bfc4cf"; font.pixelSize: 13 }
        }
    }
}
