// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: controls
    property var bridge: null
    property var panels: []
    property bool busy: false
    property bool pending: false
    property bool canUndoLayout: false
    property int seconds: 0
    property string message: bridge ? qsTr("Reading your taskbar…") : qsTr("Integrated controls need the Dagric application runner.")
    readonly property var locations: ["bottom", "top", "left", "right"]
    readonly property var alignments: ["left", "center", "right"]
    readonly property var lengths: ["fill", "fit", "custom"]
    readonly property var hides: ["none", "autohide", "dodgewindows", "windowsgobelow"]
    readonly property bool vertical: position.currentIndex > 1
    spacing: 10
    function request(action, data) {
        if (!bridge || busy) return
        busy = true
        bridge.request(action, JSON.stringify(data || null))
    }
    function selectPanel() {
        var panel = panels[selector.currentIndex]
        if (!panel) return
        size.value = panel.height; position.currentIndex = locations.indexOf(panel.location)
        alignment.currentIndex = alignments.indexOf(panel.alignment); floating.checked = panel.floating
        hiding.currentIndex = hides.indexOf(panel.hiding); length.currentIndex = lengths.indexOf(panel.lengthMode)
    }
    function apply() {
        var panel = panels[selector.currentIndex]
        if (!panel) return
        request("apply", {id:panel.id, values:{height:size.value, location:locations[position.currentIndex],
            alignment:alignments[alignment.currentIndex], floating:floating.checked,
            hiding:hides[hiding.currentIndex], lengthMode:lengths[length.currentIndex]}})
    }
    Component.onCompleted: if (bridge) request("query")
    Connections {
        target: controls.bridge
        function onResult(raw) {
            controls.busy = false
            var result = JSON.parse(raw)
            if (result.message) controls.message = result.message
            if (!result.ok) return
            if (result.panels !== undefined) {
                controls.panels = result.panels
                selector.currentIndex = Math.max(0, Math.min(selector.currentIndex, result.panels.length - 1))
                controls.selectPanel()
                controls.canUndoLayout = result.canUndoLayout
                if (!result.message) controls.message = result.panels.length ? qsTr("Changes affect only the selected taskbar.") : qsTr("No taskbar found. You can restore the default desktop layout below.")
            }
            controls.pending = result.pending || false
            controls.seconds = result.seconds || 0
            if (result.panels === undefined && !controls.pending) controls.request("query")
        }
    }
    Timer {
        interval: 1000; running: controls.pending; repeat: true
        onTriggered: { controls.seconds = Math.max(0, controls.seconds - 1); if (controls.seconds === 0 && !controls.busy) controls.request("query") }
    }
    Label { text: qsTr("Taskbar, without the guesswork"); font.bold: true; font.pointSize: Qt.application.font.pointSize * 1.25; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Rectangle {
        Layout.fillWidth: true; Layout.preferredHeight: 132; radius: 12; color: "#191c24"; border.color: "#697080"
        Accessible.role: Accessible.StaticText
        Accessible.name: qsTr("Taskbar illustration. %1, %2 pixels, %3.").arg(position.currentText).arg(size.value).arg(hiding.currentText)
        Text { anchors.centerIn: parent; text: controls.pending ? qsTr("Trial layout illustration") : qsTr("Preview — not applied yet"); color: "#d7dce6"; font.pointSize: 10 }
        Rectangle {
            readonly property real extent: Math.min(40, size.value / 2)
            width: controls.vertical ? extent : (length.currentIndex === 1 ? parent.width * 0.64 : parent.width - 16)
            height: controls.vertical ? parent.height - 16 : extent
            x: controls.vertical ? (position.currentIndex === 2 ? 8 : parent.width - width - 8) : (alignment.currentIndex === 0 ? 8 : (alignment.currentIndex === 2 ? parent.width - width - 8 : (parent.width - width) / 2))
            y: controls.vertical ? 8 : (position.currentIndex === 1 ? 8 : parent.height - height - 8)
            radius: floating.checked ? 9 : 0; color: "#971f36"; opacity: hiding.currentIndex === 1 ? 0.5 : 1
            Text { anchors.centerIn: parent; text: controls.vertical ? "●\n●\n●" : "●    ●    ●    ●"; color: "#ffffff"; font.pointSize: 9 }
        }
    }
    ColumnLayout {
        enabled: !!controls.bridge && !controls.busy && !controls.pending && controls.panels.length > 0
        Layout.fillWidth: true
        Label { text: qsTr("Taskbar to change"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ComboBox { id: selector; objectName: "panelSelector"; Layout.fillWidth: true; model: controls.panels.map(function(p, index) { return qsTr("Taskbar %1 · screen %2").arg(index + 1).arg(p.screen + 1) }); Accessible.name: qsTr("Taskbar to change"); onActivated: controls.selectPanel() }
        Label { text: qsTr("Height / thickness (pixels)"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        SpinBox { id: size; from: 24; to: 120; stepSize: 4; value: 48; editable: true; Accessible.name: qsTr("Taskbar height in pixels") }
        Label { text: qsTr("Screen edge"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ComboBox { id: position; Layout.fillWidth: true; model: [qsTr("Bottom"), qsTr("Top"), qsTr("Left"), qsTr("Right")]; Accessible.name: qsTr("Taskbar screen edge") }
        Label { text: qsTr("Length"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ComboBox { id: length; Layout.fillWidth: true; model: [qsTr("Fill the edge"), qsTr("Fit the contents"), qsTr("Keep custom length")]; Accessible.name: qsTr("Taskbar length") }
        Label { text: qsTr("Alignment of the taskbar itself"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ComboBox { id: alignment; Layout.fillWidth: true; enabled: length.currentIndex !== 0; currentIndex: 1; model: controls.vertical ? [qsTr("Bottom"), qsTr("Center"), qsTr("Top")] : [qsTr("Left"), qsTr("Center"), qsTr("Right")]; Accessible.name: qsTr("Taskbar alignment") }
        Label { text: qsTr("Alignment moves a shorter taskbar along the edge; it does not rearrange your app icons."); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        CheckBox { id: floating; checked: true; text: qsTr("Floating edges") }
        Label { text: qsTr("Visibility"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ComboBox { id: hiding; Layout.fillWidth: true; model: [qsTr("Always visible"), qsTr("Auto-hide"), qsTr("Dodge windows"), qsTr("Allow windows underneath")]; Accessible.name: qsTr("Taskbar visibility") }
        Button { text: qsTr("Try these settings"); highlighted: true; onClicked: controls.apply() }
    }
    Label { text: controls.message + (controls.pending ? "\n" + qsTr("Keep this change? Reverting in %1 seconds.").arg(controls.seconds) : ""); Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.AlertMessage }
    Flow {
        Layout.fillWidth: true; spacing: 8; visible: controls.pending
        Button { text: qsTr("Keep"); enabled: !controls.busy; onClicked: controls.request("keep") }
        Button { text: qsTr("Revert now"); enabled: !controls.busy; onClicked: controls.request("revert") }
    }
    Button { text: qsTr("Refresh taskbars"); enabled: !!controls.bridge && !controls.busy && !controls.pending; onClicked: controls.request("query") }
    Label { text: qsTr("Restore the default desktop layout"); font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Label { text: qsTr("Resets all taskbars, desktop widgets and wallpapers for this account. Open apps and personal files stay untouched. The desktop briefly restarts. A private backup and timed undo protect your previous layout; colors, fonts and display scaling are not reset."); Layout.fillWidth: true; wrapMode: Text.WordWrap }
    CheckBox { id: confirmReset; text: qsTr("I want to reset my desktop layout"); Layout.fillWidth: true }
    Flow {
        Layout.fillWidth: true; spacing: 8
        Button { text: qsTr("Preview default layout"); enabled: !!controls.bridge && confirmReset.checked && !controls.busy && !controls.pending; onClicked: { confirmReset.checked = false; controls.request("reset-layout") } }
        Button { text: qsTr("Undo last layout reset"); enabled: !!controls.bridge && controls.canUndoLayout && !controls.busy && !controls.pending; onClicked: controls.request("undo-layout") }
    }
}
