// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: page
    property string mode: "dark"
    property string layout: "eleven"
    property string icons: "modern"
    property string textSize: "normal"
    property string wallpaper: "obsidian"
    property bool initialized: false
    property bool customizing: false
    property bool reducedMotion: false
    property string assetBase: "file:///usr/share"
    readonly property bool light: mode === "light"
    readonly property color ink: light ? "#171923" : "#f5f7fa"
    readonly property color muted: light ? "#424858" : "#c5cad4"
    readonly property real basePoints: Math.max(10, Qt.application.font.pointSize)
    readonly property string wallpaperName: ({obsidian:"DagricObsidianPulse", arctic:"DagricArcticClean", aurora:"DagricAurora"})[wallpaper] || "DagricObsidianPulse"
    readonly property string iconTheme: ({modern:"DagricModern", classic:"DagricClassic", "old-school":"DagricOldSchool"})[icons] || "DagricModern"
    readonly property var choiceIds: [["dark","light"], ["classic","eleven"], ["modern","classic","old-school"], ["normal","bigger","biggest"], ["obsidian","arctic","aurora"]]
    readonly property var choiceLabels: [["Dark","Light"], ["Familiar","Centered"], ["Modern icons","Classic icons","Old school icons"], ["100% text","125% text","150% text"], ["Obsidian","Arctic","Aurora"]]
    readonly property string profile: [mode, layout, icons, textSize, wallpaper].map(function(value, i) { return choiceLabels[i][choiceIds[i].indexOf(value)] }).join(" · ")
    readonly property int textPercent: textSize === "biggest" ? 150 : (textSize === "bigger" ? 125 : 100)
    readonly property var properties: ["mode", "layout", "icons", "textSize", "wallpaper"]
    readonly property var headings: [qsTr("Appearance"), qsTr("Taskbar"), qsTr("Icon style"), qsTr("Application text"), qsTr("Background")]
    readonly property var names: [[qsTr("Dark"), qsTr("Light")], [qsTr("Familiar"), qsTr("Centered")], [qsTr("Modern"), qsTr("Classic"), qsTr("Old school")], [qsTr("Normal · 100%"), qsTr("Bigger · 125%"), qsTr("Biggest · 150%")], [qsTr("Obsidian"), qsTr("Arctic"), qsTr("Aurora")]]
    readonly property var details: [[qsTr("Obsidian & graphite"), qsTr("Bright & clear")], [qsTr("Apps on the left"), qsTr("Apps in the middle")], [qsTr("Dimensional"), qsTr("Enamel badges"), qsTr("Pixel-inspired")], [qsTr("Standard text"), qsTr("Easier to read"), qsTr("Large text")], [qsTr("Red & black"), qsTr("Open & bright"), qsTr("Color & atmosphere")]]
    color: light ? "#f1f3f7" : "#101218"
    function storeChoice() { if (initialized) config.packageChoice = profile }
    function revealChoice(choice) {
        var view = scroll.contentItem
        var y = choice.mapToItem(view.contentItem, 0, 0).y
        if (y < view.contentY) view.contentY = y
        else if (y + choice.height > view.contentY + view.height)
            view.contentY = Math.min(Math.max(0, view.contentHeight - view.height), y + choice.height - view.height)
    }
    function useRecommended() {
        mode = "dark"; layout = "eleven"; icons = "modern"; textSize = "normal"; wallpaper = "obsidian"
        customizing = false
    }
    onProfileChanged: storeChoice()
    Component.onCompleted: {
        var old = String(config.packageChoice || "").split(" · ")
        if (old.length === 5 && old.every(function(value, i) { return choiceLabels[i].indexOf(value) >= 0 })) {
            var ids = old.map(function(value, i) { return choiceIds[i][choiceLabels[i].indexOf(value)] })
            mode = ids[0]; layout = ids[1]; icons = ids[2]; textSize = ids[3]; wallpaper = ids[4]
        }
        customizing = profile !== "Dark · Centered · Modern icons · 100% text · Obsidian"
        initialized = true; storeChoice()
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Math.min(20, page.width / 30); spacing: 10
        Text { text: qsTr("Make it feel like yours."); color: page.ink; font.pointSize: page.basePoints * 1.6; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Flow {
            Layout.fillWidth: true; spacing: 8
            Button { objectName: "recommended"; text: qsTr("Use recommended"); highlighted: !page.customizing; onClicked: page.useRecommended() }
            Button { objectName: "customize"; text: qsTr("Customize"); highlighted: page.customizing; onClicked: page.customizing = true }
        }
        DesktopPreview {
            objectName: "persistentPreview"
            Layout.fillWidth: true; Layout.preferredHeight: Math.max(110, Math.min(190, page.height * 0.3))
            light: page.light; familiar: page.layout === "classic"; textPercent: page.textPercent
            assetBase: page.assetBase; wallpaperName: page.wallpaperName; iconTheme: page.iconTheme
            reducedMotion: page.reducedMotion
        }
        ScrollView {
            id: scroll
            objectName: "choicesScroll"
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 50
            clip: true; contentWidth: Math.max(0, availableWidth - 16)
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            ColumnLayout {
                width: Math.max(0, scroll.availableWidth - 16); spacing: 12
                Text {
                    visible: !page.customizing; Layout.fillWidth: true; wrapMode: Text.WordWrap
                    color: page.ink; font.pointSize: page.basePoints
                    text: qsTr("Ready to go. Choose Next to create your account. These preferences will be waiting after installation — no second setup wizard. You can change them later.")
                }
                Repeater {
                    model: page.customizing ? 5 : 0
                    ColumnLayout {
                        id: group
                        required property int index
                        Layout.fillWidth: true; spacing: 8
                        Text { text: page.headings[group.index]; color: page.ink; font.pointSize: page.basePoints * 1.1; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Flow {
                            Layout.fillWidth: true; spacing: 8
                            Repeater {
                                model: page.choiceIds[group.index]
                                ProfileChoice {
                                    required property int index
                                    required property string modelData
                                    width: Math.min(implicitWidth, parent.width)
                                    light: page.light
                                    text: page.names[group.index][index]; detail: page.details[group.index][index]
                                    selected: page[page.properties[group.index]] === modelData
                                    onClicked: page[page.properties[group.index]] = modelData
                                    onActiveFocusChanged: if (activeFocus) page.revealChoice(this)
                                }
                            }
                        }
                    }
                }
                CheckBox { text: qsTr("Reduce preview motion"); checked: page.reducedMotion; onToggled: page.reducedMotion = checked; palette.windowText: page.ink }
                Text {
                    Layout.fillWidth: true; wrapMode: Text.WordWrap; color: page.muted; font.pointSize: page.basePoints * 0.9
                    text: qsTr("Application text: %1%. These choices do not change partitions or accounts, or install extra apps. Display scaling follows your screen.").arg(page.textPercent)
                }
            }
        }
    }
}
