// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
AbstractButton {
    id: control
    property string detail: ""
    property bool selected: false
    property bool light: false
    readonly property real basePoints: Math.max(10, Qt.application.font.pointSize)
    implicitWidth: Math.max(174, basePoints * 17)
    implicitHeight: Math.max(80, copy.implicitHeight + 24)
    Accessible.name: text + (selected ? qsTr(", selected") : "") + ". " + detail
    Accessible.checkable: true
    Accessible.checked: selected
    background: Rectangle {
        radius: 10
        color: control.light ? (control.selected ? "#f9dce2" : (control.hovered ? "#e1e5ed" : "#ffffff")) : (control.selected ? "#341821" : (control.hovered ? "#252833" : "#191c24"))
        border.color: control.activeFocus ? (control.light ? "#171923" : "#ffffff") : (control.selected ? "#bc2543" : "#777e8d")
        border.width: control.activeFocus || control.selected ? 2 : 1
    }
    contentItem: Item {
        Column {
            id: copy
            x: 14; y: 12; width: parent.width - 26
            spacing: 5
            Text { width: parent.width; text: (control.selected ? "✓ " : "") + control.text; color: control.light ? "#171923" : "#f5f7fa"; font.pointSize: control.basePoints; font.bold: true; wrapMode: Text.WordWrap }
            Text { width: parent.width; text: control.detail; color: control.light ? "#424858" : "#c5cad4"; font.pointSize: control.basePoints * 0.9; wrapMode: Text.WordWrap }
        }
    }
}
