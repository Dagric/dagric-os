// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
AbstractButton {
    id: control
    property string detail: ""
    property bool selected: false
    implicitWidth: 174
    implicitHeight: 80
    Accessible.name: text + (selected ? qsTr(", selected") : "") + ". " + detail
    background: Rectangle {
        radius: 10
        color: control.selected ? "#341821" : (control.hovered ? "#252833" : "#191c24")
        border.color: control.activeFocus ? "#ffffff" : (control.selected ? "#ef6d81" : "#454956")
        border.width: control.activeFocus || control.selected ? 2 : 1
    }
    contentItem: Item {
        Column {
            anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 12; anchors.topMargin: 11
            spacing: 5
            Text { width: parent.width; text: (control.selected ? "✓ " : "") + control.text; color: "#f5f7fa"; font.pixelSize: 15; font.bold: true; wrapMode: Text.WordWrap }
            Text { width: parent.width; text: control.detail; color: "#bfc4cf"; font.pixelSize: 12; wrapMode: Text.WordWrap }
        }
    }
}
