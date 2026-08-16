// SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Dagric OS — "Family Limits": the window a parent uses to set screen time.
//
// THE VIEW ONLY, exactly like the first-run wizard. QML cannot run programs, and
// a window that could would be a privilege problem rather than a convenience.
// /usr/bin/dagric-family reads the catalogue this window is handed, and
// /usr/lib/dagric/family-apply does the privileged write behind pkexec. This
// file decides nothing and can break nothing.
//
//   dagric-family   writes a catalogue (JSON) and passes it as --catalog=PATH
//   this window     prints  @DAGRIC@<COMMAND>|<argument>  when Save is pressed
//
// The @DAGRIC@ marker is what separates the protocol from ordinary Qt chatter
// on the same pipe, so a stray warning can never be read as an order.
//
// WHY THIS WINDOW EXISTS AT ALL, when timekpr-next ships its own admin GUI: that
// GUI carries translations for Italian and Latvian only. Dagric ships six
// languages. Handing a German, French, Spanish or Brazilian parent an English
// dialog for the one feature they are most likely to get wrong is the defect
// 465dc7b was written to fix for Qt's own strings, and it would be worse here,
// because getting this wrong locks a child out of their homework.
//
// ============================================================ ACCESSIBILITY
//
// Same standard the wizard is held to, and for a stronger reason: a parent
// setting limits on a child's account may well be the household member using a
// screen reader. Qt only builds an accessible object for an Item once
// Accessible.role is set — a bare Rectangle with a MouseArea is furniture, not a
// control, and is ABSENT from the tree rather than badly labelled. So every
// control below declares role, name and state, every decorative shape declares
// Accessible.ignored, and nothing is operable by mouse alone.
//
// The numbers are announced as words. "150" read aloud tells a parent nothing;
// "2 hours 30 minutes" is the actual setting. Accessible.name is built from the
// same formatter the label uses, so the two can never drift.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: app
    visible: true
    width: 760
    height: 620
    minimumWidth: 560
    minimumHeight: 520
    title: qsTr("Family Limits")

    // ---------------------------------------------------------------- state
    property var people: []
    property int idx: -1
    property var who: idx >= 0 && idx < people.length ? people[idx] : null

    property bool limitsOn: false
    property int  minutes: 120
    property int  bedFrom: 21
    property int  bedTo: 7
    property string lockout: "lock"
    property bool loaded: false

    readonly property color line: Qt.rgba(0.5, 0.5, 0.5, 0.28)

    function send(cmd, arg) { console.log("@DAGRIC@" + cmd + "|" + arg) }

    // Minutes as a person says them. Used for the visible label AND for
    // Accessible.name, so a screen reader and the screen always agree.
    function spoken(m) {
        var h = Math.floor(m / 60), r = m % 60
        if (h === 0) return qsTr("%1 minutes").arg(r)
        if (r === 0) return h === 1 ? qsTr("1 hour") : qsTr("%1 hours").arg(h)
        return qsTr("%1 h %2 min").arg(h).arg(r)
    }
    function hh(h) { return (h < 10 ? "0" + h : "" + h) + ":00" }

    function loadPerson(p) {
        if (!p) return
        limitsOn = p.known && p.minutes > 0 && p.minutes < 1440
        minutes  = (p.minutes > 0 && p.minutes < 1440) ? p.minutes : 120
        bedFrom  = p.bedFrom
        bedTo    = p.bedTo
        lockout  = p.lockout === "terminate" ? "terminate" : "lock"
    }

    Component.onCompleted: {
        var path = ""
        for (var i = 0; i < Qt.application.arguments.length; i++) {
            var a = Qt.application.arguments[i]
            if (a.indexOf("--catalog=") === 0) path = a.substring(10)
        }
        if (path === "") return
        var xhr = new XMLHttpRequest()
        xhr.open("GET", "file://" + path, false)
        xhr.send(null)
        try {
            people = JSON.parse(xhr.responseText).people
        } catch (e) {
            people = []
        }
        // Open on the first person who can actually be limited, so the common
        // case needs no clicks at all.
        for (var j = 0; j < people.length; j++) {
            if (!people[j].protected) { idx = j; break }
        }
        if (idx < 0 && people.length > 0) idx = 0
        loadPerson(who)
        loaded = true
    }

    // ------------------------------------------------------------------ chrome
    header: ToolBar {
        Accessible.ignored: true
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            Label {
                text: qsTr("Family Limits")
                font.pixelSize: 17
                font.weight: Font.DemiBold
                Accessible.role: Accessible.StaticText
                Accessible.name: text
            }
            Item { Layout.fillWidth: true }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: qsTr("Set how long someone can use this computer each day, and the hours when it locks itself. Their files and their account are not touched.")
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }

        // --------------------------------------------------------- who
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Label {
                text: qsTr("Person:")
                Accessible.role: Accessible.StaticText
                Accessible.name: text
            }
            ComboBox {
                id: personBox
                Layout.fillWidth: true
                model: app.people
                textRole: "name"
                currentIndex: app.idx
                enabled: app.people.length > 0
                onActivated: { app.idx = currentIndex; app.loadPerson(app.who) }
                Accessible.role: Accessible.ComboBox
                Accessible.name: qsTr("Person to set limits for")
                Accessible.description: app.who ? app.who.name : ""
            }
        }

        // The last administrator can never be limited. Explained here as well as
        // refused in family-apply, because a greyed-out control with no reason
        // is indistinguishable from a bug.
        Label {
            Layout.fillWidth: true
            visible: app.who !== null && app.who.protected
            wrapMode: Text.WordWrap
            color: "#c8502d"
            text: qsTr("This is the only administrator account on this computer. Limits cannot be set on it, because there would be no way back in. Create a second administrator account first.")
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }
        Label {
            Layout.fillWidth: true
            visible: app.who !== null && !app.who.protected && !app.who.known
            wrapMode: Text.WordWrap
            text: qsTr("This person has not signed in yet, so there is nothing to change. Ask them to sign in once, then come back.")
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: app.line
            Accessible.ignored: true
        }

        // --------------------------------------------------------- the switch
        Switch {
            id: onSwitch
            text: qsTr("Limit this person's screen time")
            checked: app.limitsOn
            enabled: app.who !== null && !app.who.protected && app.who.known
            onToggled: app.limitsOn = checked
            Accessible.role: Accessible.CheckBox
            Accessible.name: text
            Accessible.checked: checked
        }

        // --------------------------------------------------------- the settings
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 14
            enabled: onSwitch.checked && onSwitch.enabled
            opacity: enabled ? 1.0 : 0.45

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Label {
                    text: qsTr("Time allowed each day: %1").arg(app.spoken(app.minutes))
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
                Slider {
                    id: minSlider
                    Layout.fillWidth: true
                    from: 15; to: 720; stepSize: 15
                    value: app.minutes
                    onMoved: app.minutes = Math.round(value)
                    // The announced value is the sentence, not the raw number:
                    // "one hundred and fifty" tells a parent nothing useful.
                    Accessible.role: Accessible.Slider
                    Accessible.name: qsTr("Time allowed each day")
                    Accessible.description: app.spoken(app.minutes)
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Label {
                    text: app.bedFrom === app.bedTo
                          ? qsTr("Bedtime: none — the computer never locks by the clock")
                          : qsTr("The computer locks from %1 to %2").arg(app.hh(app.bedFrom)).arg(app.hh(app.bedTo))
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
                RowLayout {
                    spacing: 10
                    Label {
                        text: qsTr("From")
                        Accessible.role: Accessible.StaticText
                        Accessible.name: text
                    }
                    SpinBox {
                        from: 0; to: 23
                        value: app.bedFrom
                        onValueModified: app.bedFrom = value
                        textFromValue: function(v) { return app.hh(v) }
                        Accessible.role: Accessible.SpinBox
                        Accessible.name: qsTr("Bedtime starts at")
                        Accessible.description: app.hh(app.bedFrom)
                    }
                    Label {
                        text: qsTr("until")
                        Accessible.role: Accessible.StaticText
                        Accessible.name: text
                    }
                    SpinBox {
                        from: 0; to: 23
                        value: app.bedTo
                        onValueModified: app.bedTo = value
                        textFromValue: function(v) { return app.hh(v) }
                        Accessible.role: Accessible.SpinBox
                        Accessible.name: qsTr("Bedtime ends at")
                        Accessible.description: app.hh(app.bedTo)
                    }
                    Item { Layout.fillWidth: true }
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                    opacity: 0.75
                    text: qsTr("Set both to the same hour for no bedtime at all.")
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Label {
                    text: qsTr("When the time is up:")
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
                // LOCK IS THE DEFAULT AND SIGN OUT IS THE OPT-IN, which is the
                // reverse of timekpr's own default. Ending the session closes
                // whatever a child had open, so the first thing a parent hears
                // about this feature would be lost homework — and the blame
                // lands on the parent who switched it on.
                RadioButton {
                    text: qsTr("Lock the screen — nothing is closed, nothing is lost")
                    checked: app.lockout === "lock"
                    onToggled: if (checked) app.lockout = "lock"
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: text
                    Accessible.checked: checked
                }
                RadioButton {
                    text: qsTr("Sign out — closes everything that is open")
                    checked: app.lockout === "terminate"
                    onToggled: if (checked) app.lockout = "terminate"
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: text
                    Accessible.checked: checked
                }
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: app.line
            Accessible.ignored: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Button {
                text: qsTr("Remove all limits")
                enabled: app.who !== null && !app.who.protected && app.who.known
                onClicked: {
                    app.send("REMOVE", app.who.user)
                    app.limitsOn = false
                }
                Accessible.role: Accessible.Button
                Accessible.name: text
                Accessible.description: qsTr("Lets this person use the computer at any time, for as long as they like")
            }
            Item { Layout.fillWidth: true }
            Button {
                text: qsTr("Close")
                onClicked: Qt.quit()
                Accessible.role: Accessible.Button
                Accessible.name: text
            }
            Button {
                text: qsTr("Save")
                highlighted: true
                enabled: app.who !== null && !app.who.protected && app.who.known && onSwitch.checked
                onClicked: app.send("SET", app.who.user + ";" + app.minutes + ";"
                                    + app.bedFrom + ";" + app.bedTo + ";" + app.lockout)
                Accessible.role: Accessible.Button
                Accessible.name: text
                Accessible.description: app.who
                    ? qsTr("Save these limits for %1").arg(app.who.name) : text
            }
        }
    }
}
