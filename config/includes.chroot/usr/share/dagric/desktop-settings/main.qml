// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: window
    visible: true
    title: qsTr("Desktop & taskbar")
    width: Math.min(820, Screen.desktopAvailableWidth)
    height: Math.min(660, Screen.desktopAvailableHeight)
    minimumWidth: 420; minimumHeight: 380
    color: palette.window
    property string assetBase: "file:///usr/share"
    property string iconTheme: "DagricModern"
    Component.onCompleted: {
        for (var arg of Qt.application.arguments) {
            var value = arg.replace(/^--icon-theme=/, "")
            if (["DagricModern", "DagricClassic", "DagricOldSchool"].indexOf(value) >= 0) iconTheme = value
        }
    }
    property var actions: [
        {key:"appearance", title:qsTr("Colors, icons & layout"), icon:"dagric-appearance", detail:qsTr("See the styles before choosing. Keep a change or let the preview revert automatically.")},
        {key:"panel", title:qsTr("Advanced taskbar editing"), icon:"dagric-looks", detail:qsTr("Move individual widgets or change detailed app behavior using Plasma Edit Mode.")},
        {key:"widgets", title:qsTr("Add or manage widgets"), icon:"dagric-hub", detail:qsTr("Open the widget browser. Drag a widget onto the desktop or taskbar; use Edit Mode to move or remove it.")},
        {key:"fonts", title:qsTr("Make text easier to read"), icon:"dagric-display", detail:qsTr("Choose application fonts and sizes. Use Display size for icons, windows and everything else together.")},
        {key:"display", title:qsTr("Display size"), icon:"dagric-display", detail:qsTr("Change screen scaling with a timed Keep or Revert preview.")}
    ]
    function requestAction(key) {
        if (actions.some(function(item) { return item.key === key }))
            console.log("@DAGRIC_DESKTOP@" + key)
    }
    ScrollView {
        id: scroll
        anchors.fill: parent; anchors.margins: 24
        contentWidth: availableWidth; clip: true
        ColumnLayout {
            width: scroll.availableWidth; spacing: 14
            Text { text: qsTr("Your desktop. Your way."); color: window.palette.windowText; font.pointSize: Qt.application.font.pointSize * 1.7; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Text { text: qsTr("One place for the controls that make Dagric feel like yours."); color: window.palette.windowText; font.pointSize: Qt.application.font.pointSize; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            PanelControls { Layout.fillWidth: true; bridge: typeof desktopBridge !== "undefined" ? desktopBridge : null }
            Repeater {
                model: window.actions
                delegate: AbstractButton {
                    id: card
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: Math.max(94, copy.implicitHeight + 30)
                    Accessible.name: modelData.title + ". " + modelData.detail
                    onClicked: window.requestAction(modelData.key)
                    background: Rectangle {
                        radius: 12
                        color: card.hovered ? window.palette.alternateBase : window.palette.base
                        border.width: card.activeFocus ? 2 : 1
                        border.color: card.activeFocus ? window.palette.highlight : window.palette.mid
                        Rectangle { width: 4; height: parent.height - 32; radius: 2; anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; color: "#b82036" }
                    }
                    contentItem: Item {
                        Image { anchors.left: parent.left; anchors.leftMargin: 24; anchors.verticalCenter: parent.verticalCenter; width: 40; height: 40; source: window.assetBase + "/icons/" + window.iconTheme + "/48x48/apps/" + card.modelData.icon + ".png"; fillMode: Image.PreserveAspectFit }
                        Column {
                            id: copy
                            x: 80; y: (parent.height - height) / 2; width: parent.width - 108; spacing: 6
                            Text { width: parent.width; text: card.modelData.title; font.pointSize: Qt.application.font.pointSize * 1.15; font.bold: true; color: window.palette.text; wrapMode: Text.WordWrap }
                            Text { width: parent.width; text: card.modelData.detail; font.pointSize: Qt.application.font.pointSize; color: window.palette.text; wrapMode: Text.WordWrap }
                        }
                    }
                }
            }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: window.palette.windowText; font.pointSize: Qt.application.font.pointSize; text: qsTr("Changes affect your desktop, not other accounts. Your files and partitions are untouched. Third-party widgets can run code: install only ones you trust.") }
        }
    }
}
