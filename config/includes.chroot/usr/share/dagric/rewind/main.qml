// SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Dagric Rewind is a view, not a privileged program.  It reads a root-owned
// summary copied into a private temporary directory by /usr/bin/dagric-rewind
// and emits only the allow-listed @DAGRIC@ protocol documented there.
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: app
    visible: true
    width: 1080
    height: 720
    minimumWidth: 720
    minimumHeight: 540
    title: "Dagric Rewind"
    color: "#07111f"

    FontMetrics { id: systemFont }
    readonly property real uiScale: Math.max(1.0, Math.min(1.45, systemFont.height / 17.0))
    readonly property color blue: "#4eb4ff"
    readonly property color blueSoft: "#173b59"
    readonly property color green: "#55d69e"
    readonly property color amber: "#f6c66a"
    readonly property color red: "#ff818e"
    readonly property color ink: "#eef7ff"
    readonly property color muted: "#9fb3c8"
    readonly property color panel: "#101e2e"
    readonly property color panelRaised: "#16283b"
    readonly property color line: "#294157"
    property bool reducedMotion: false
    property string catalogFile: ""
    property string loadError: ""
    property string lastReviewKey: ""
    property var state: ({
        "ready": false,
        "reason": "loading",
        "filesystem": "",
        "privacy": {"screenRecording": false, "cloud": false, "account": false},
        "presets": [], "active": null, "sessions": [], "snapshots": [], "review": null
    })
    property int revision: 0

    function scaled(value) { return Math.round(value * uiScale); }

    function argument(name) {
        var args = Qt.application.arguments;
        var prefix = "--" + name + "=";
        for (var i = 0; i < args.length; ++i) {
            if (args[i].indexOf(prefix) === 0)
                return args[i].substring(prefix.length);
        }
        return "";
    }

    function send(message) {
        console.log("@DAGRIC@" + message);
    }

    function loadCatalog() {
        if (!catalogFile.length)
            return;
        // XMLHttpRequest is a QML JavaScript global, so it has no object ID to
        // qualify even though qmllint's generic unqualified rule asks for one.
        // qmllint disable unqualified
        var request = new XMLHttpRequest();
        request.open("GET", "file://" + catalogFile);
        request.onreadystatechange = function() {
            if (request.readyState !== XMLHttpRequest.DONE)
                return;
            if (request.status !== 0 && request.status !== 200) {
                loadError = "The Rewind timeline could not be read.";
                return;
            }
            try {
                var incoming = JSON.parse(request.responseText);
                var reviewKey = incoming.review ? incoming.review.pre + ":" + incoming.review.post : "";
                var revealReview = reviewKey.length > 0 && reviewKey !== lastReviewKey;
                state = incoming;
                lastReviewKey = reviewKey;
                loadError = "";
                revision += 1;
                if (revealReview) {
                    Qt.callLater(function() {
                        var flick = bodyScroll.contentItem;
                        flick.contentY = Math.max(0, flick.contentHeight - flick.height);
                    });
                }
            } catch (error) {
                loadError = "The Rewind timeline is damaged or incomplete.";
            }
        }
        request.send();
    }

    function compactDate(value) {
        if (!value || !value.length)
            return "Time unavailable";
        return value.replace("T", "  ").replace("Z", " UTC").substring(0, 25);
    }

    function unavailableTitle() {
        switch (state.reason) {
        case "live": return "Install Dagric to turn on Rewind";
        case "filesystem": return "This installation is not using Btrfs";
        case "snapper": return "The snapshot service is missing";
        case "configuration": return "Rewind needs to be set up";
        default: return "Loading your timeline…";
        }
    }

    function unavailableBody() {
        switch (state.reason) {
        case "live":
            return "The live USB forgets changes when it shuts down. Rewind becomes available automatically on a standard Dagric installation.";
        case "filesystem":
            return "Rewind protects system changes with Btrfs snapshots. Your files are untouched, but this installation cannot provide instant system checkpoints.";
        case "snapper":
            return "Update Dagric to restore Snapper and Btrfs Assistant. No existing snapshot has been removed.";
        case "configuration":
            return "Run Dagric's snapshot setup once, then reopen this window. Rewind will never pretend it can undo a machine that has no snapshots.";
        default:
            return "Reading local system checkpoints. Nothing is being uploaded or recorded from your screen.";
        }
    }

    Component.onCompleted: {
        catalogFile = argument("catalog");
        reducedMotion = argument("reduced-motion").toLowerCase() === "true";
        if (!catalogFile.length)
            loadError = "Open Dagric Rewind from the application menu instead of opening its QML file directly.";
        else
            loadCatalog();
    }

    onClosing: send("QUIT|")

    Timer {
        interval: 850
        running: app.visible && app.catalogFile.length > 0
        repeat: true
        onTriggered: app.loadCatalog()
    }

    background: Rectangle {
        color: "#07111f"
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0c1b2d" }
            GradientStop { position: 0.55; color: "#081523" }
            GradientStop { position: 1.0; color: "#06101c" }
        }

        Rectangle {
            width: app.scaled(520); height: width; radius: width / 2
            x: parent.width - width * 0.58; y: -height * 0.58
            color: "#163f62"; opacity: 0.28
        }
        Rectangle {
            width: app.scaled(360); height: width; radius: width / 2
            x: -width * 0.58; y: parent.height - height * 0.45
            color: "#103c36"; opacity: 0.16
        }
    }

    component Capsule: Rectangle {
        id: capsule
        property alias text: capsuleLabel.text
        property color accent: app.blue
        implicitWidth: capsuleLabel.implicitWidth + app.scaled(22)
        implicitHeight: app.scaled(28)
        radius: height / 2
        color: Qt.rgba(accent.r, accent.g, accent.b, 0.12)
        border.color: Qt.rgba(accent.r, accent.g, accent.b, 0.48)
        border.width: 1
        Label {
            id: capsuleLabel
            anchors.centerIn: parent
            color: capsule.accent
            font.pixelSize: app.scaled(11)
            font.weight: Font.DemiBold
            font.letterSpacing: 0.7
        }
    }

    component RewindButton: Button {
        id: control
        property color accent: app.blue
        property bool quiet: false
        implicitHeight: app.scaled(42)
        leftPadding: app.scaled(18); rightPadding: app.scaled(18)
        font.pixelSize: app.scaled(14)
        font.weight: Font.DemiBold
        palette.buttonText: enabled ? (quiet ? app.ink : "#05111c") : app.muted
        contentItem: Label {
            text: control.text
            color: control.enabled ? (control.quiet ? app.ink : "#05111c") : app.muted
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: app.scaled(10)
            color: !control.enabled ? "#1c2a38" : control.quiet ?
                       (control.down ? "#27445e" : control.hovered ? "#203a51" : "#172b3d") :
                       (control.down ? Qt.darker(control.accent, 1.18) :
                        control.hovered ? Qt.lighter(control.accent, 1.08) : control.accent)
            border.color: control.quiet ? (control.activeFocus ? app.blue : app.line) : "transparent"
            border.width: control.activeFocus ? 2 : 1
            Behavior on color { ColorAnimation { duration: app.reducedMotion ? 0 : 120 } }
        }
    }

    component SectionLabel: Label {
        color: app.muted
        font.pixelSize: app.scaled(11)
        font.weight: Font.DemiBold
        font.letterSpacing: 1.2
    }

    component EmptyLine: Rectangle {
        color: app.line
        opacity: 0.8
        implicitHeight: 1
        Layout.fillWidth: true
    }

    header: Rectangle {
        implicitHeight: app.scaled(86)
        color: Qt.rgba(0.035, 0.075, 0.12, 0.92)
        border.color: app.line
        border.width: 0

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: app.scaled(30)
            anchors.rightMargin: app.scaled(30)
            spacing: app.scaled(18)

            Rectangle {
                Layout.preferredWidth: app.scaled(45)
                Layout.preferredHeight: app.scaled(45)
                radius: app.scaled(14)
                color: app.blueSoft
                border.color: "#326f9d"
                Label {
                    anchors.centerIn: parent
                    text: "↶"
                    color: app.blue
                    font.pixelSize: app.scaled(28)
                    font.weight: Font.DemiBold
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Label {
                    text: "Dagric Rewind"
                    color: app.ink
                    font.pixelSize: app.scaled(22)
                    font.weight: Font.Bold
                }
                Label {
                    text: "Your computer has an Undo button."
                    color: app.muted
                    font.pixelSize: app.scaled(13)
                }
            }

            Capsule { text: "LOCAL ONLY"; accent: app.green }
            Capsule { text: "NO SCREEN RECORDING"; accent: app.blue }

            RewindButton {
                text: "Refresh"
                quiet: true
                Accessible.name: "Refresh the Rewind timeline"
                onClicked: app.send("REFRESH|")
            }
        }
    }

    ScrollView {
        id: bodyScroll
        anchors.fill: parent
        anchors.margins: app.scaled(22)
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: app.scaled(18)

            Rectangle {
                visible: app.loadError.length > 0
                Layout.fillWidth: true
                implicitHeight: errorRow.implicitHeight + app.scaled(30)
                radius: app.scaled(14)
                color: "#3a2028"
                border.color: app.red
                RowLayout {
                    id: errorRow
                    anchors.fill: parent
                    anchors.margins: app.scaled(15)
                    Label { text: "!"; color: app.red; font.pixelSize: app.scaled(22); font.weight: Font.Bold }
                    Label {
                        Layout.fillWidth: true
                        text: app.loadError
                        wrapMode: Text.Wrap
                        color: app.ink
                        font.pixelSize: app.scaled(14)
                    }
                }
            }

            Rectangle {
                visible: !app.state.ready && !app.loadError.length
                Layout.fillWidth: true
                implicitHeight: unavailableColumn.implicitHeight + app.scaled(52)
                radius: app.scaled(20)
                color: app.panel
                border.color: app.line

                ColumnLayout {
                    id: unavailableColumn
                    anchors.fill: parent
                    anchors.margins: app.scaled(26)
                    spacing: app.scaled(10)
                    Capsule { text: "HONEST RECOVERY STATUS"; accent: app.amber }
                    Label {
                        text: app.unavailableTitle()
                        color: app.ink
                        font.pixelSize: app.scaled(25)
                        font.weight: Font.Bold
                    }
                    Label {
                        Layout.fillWidth: true
                        text: app.unavailableBody()
                        color: app.muted
                        font.pixelSize: app.scaled(15)
                        lineHeight: 1.35
                        wrapMode: Text.Wrap
                    }
                    Label {
                        text: "Detected root filesystem: " + (app.state.filesystem || "unknown")
                        color: app.amber
                        font.pixelSize: app.scaled(12)
                    }
                }
            }

            RowLayout {
                visible: app.state.ready
                Layout.fillWidth: true
                spacing: app.scaled(18)

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: app.scaled(18)

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: heroColumn.implicitHeight + app.scaled(44)
                        radius: app.scaled(20)
                        color: app.state.active ? "#112f32" : app.panel
                        border.color: app.state.active ? "#2d856d" : app.line

                        ColumnLayout {
                            id: heroColumn
                            anchors.fill: parent
                            anchors.margins: app.scaled(22)
                            spacing: app.scaled(12)

                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    SectionLabel { text: app.state.active ? "REWIND SESSION RUNNING" : "START BEFORE YOU CHANGE SOMETHING" }
                                    Label {
                                        text: app.state.active ? app.state.active.label : "Make the next change reversible"
                                        color: app.ink
                                        font.pixelSize: app.scaled(23)
                                        font.weight: Font.Bold
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: app.state.active ?
                                            "Started " + app.compactDate(app.state.active.startedAt) + ". Finish when your change is complete." :
                                            "Rewind pairs a before-and-after checkpoint, then explains what changed. It records system paths—not your screen, typing, or documents."
                                        color: app.muted
                                        font.pixelSize: app.scaled(14)
                                        lineHeight: 1.3
                                        wrapMode: Text.Wrap
                                    }
                                }
                                RewindButton {
                                    visible: app.state.active !== null
                                    text: "Finish & review"
                                    accent: app.green
                                    Accessible.name: "Finish the current Rewind session"
                                    onClicked: app.send("FINISH|")
                                }
                            }

                            GridLayout {
                                visible: app.state.active === null
                                Layout.fillWidth: true
                                columns: width > app.scaled(560) ? 2 : 1
                                uniformCellWidths: true
                                columnSpacing: app.scaled(10)
                                rowSpacing: app.scaled(10)

                                Repeater {
                                    model: app.state.presets || []
                                    delegate: Button {
                                        id: presetButton
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: app.scaled(98)
                                        Accessible.name: "Start Rewind session: " + modelData.label
                                        onClicked: app.send("START|" + modelData.id)
                                        contentItem: Column {
                                            spacing: app.scaled(6)
                                            Label {
                                                width: parent.width
                                                text: presetButton.modelData.label
                                                color: app.ink
                                                font.pixelSize: app.scaled(14)
                                                font.weight: Font.DemiBold
                                                wrapMode: Text.Wrap
                                            }
                                            Label {
                                                width: parent.width
                                                text: presetButton.modelData.prompt
                                                color: app.muted
                                                font.pixelSize: app.scaled(11)
                                                wrapMode: Text.Wrap
                                                maximumLineCount: 3
                                                elide: Text.ElideRight
                                            }
                                        }
                                        background: Rectangle {
                                            radius: app.scaled(12)
                                            color: presetButton.down ? "#21425a" : presetButton.hovered ? "#1b354b" : app.panelRaised
                                            border.color: presetButton.activeFocus ? app.blue : app.line
                                            border.width: presetButton.activeFocus ? 2 : 1
                                            Behavior on color { ColorAnimation { duration: app.reducedMotion ? 0 : 130 } }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: proofColumn.implicitHeight + app.scaled(38)
                        radius: app.scaled(18)
                        color: app.panel
                        border.color: app.line

                        ColumnLayout {
                            id: proofColumn
                            anchors.fill: parent
                            anchors.margins: app.scaled(19)
                            spacing: app.scaled(10)
                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    SectionLabel { text: "A CHECKPOINT YOU CAN NAME AND TRUST" }
                                    Label {
                                        text: "Mark this moment as known-good"
                                        color: app.ink
                                        font.pixelSize: app.scaled(18)
                                        font.weight: Font.DemiBold
                                    }
                                }
                                RewindButton {
                                    text: "Create checkpoint"
                                    quiet: true
                                    enabled: app.state.active === null
                                    Accessible.name: "Create a known-good system checkpoint"
                                    onClicked: app.send("CHECKPOINT|")
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "Useful before travel, a deadline, or a major upgrade. Rewind keeps the checkpoint in Dagric's normal snapshot retention system."
                                color: app.muted
                                font.pixelSize: app.scaled(13)
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    Rectangle {
                        visible: app.state.review !== null
                        Layout.fillWidth: true
                        implicitHeight: reviewColumn.implicitHeight + app.scaled(40)
                        radius: app.scaled(18)
                        color: "#111f30"
                        border.color: "#315777"

                        ColumnLayout {
                            id: reviewColumn
                            anchors.fill: parent
                            anchors.margins: app.scaled(20)
                            spacing: app.scaled(12)

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: app.scaled(8)
                                SectionLabel { text: "CHANGE REVIEW" }
                                Label {
                                    Layout.fillWidth: true
                                    text: app.state.review ? app.state.review.total + " meaningful system paths changed" : ""
                                    color: app.ink
                                    font.pixelSize: app.scaled(20)
                                    font.weight: Font.Bold
                                    wrapMode: Text.Wrap
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: app.scaled(8)
                                    Capsule { text: app.state.review ? app.state.review.added + " ADDED" : ""; accent: app.green }
                                    Capsule { text: app.state.review ? app.state.review.modified + " CHANGED" : ""; accent: app.blue }
                                    Capsule { text: app.state.review ? app.state.review.deleted + " REMOVED" : ""; accent: app.red }
                                }
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: app.scaled(8)
                                Repeater {
                                    model: app.state.review ? app.state.review.categories : []
                                    delegate: Capsule {
                                        id: categoryCapsule
                                        required property var modelData
                                        text: categoryCapsule.modelData.name.toUpperCase() + "  " + categoryCapsule.modelData.count
                                        accent: app.amber
                                    }
                                }
                            }

                            EmptyLine {}

                            Repeater {
                                model: app.state.review ? app.state.review.paths.slice(0, 10) : []
                                delegate: RowLayout {
                                    id: changedPathRow
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Label {
                                        text: changedPathRow.modelData.kind === "added" ? "+" : changedPathRow.modelData.kind === "deleted" ? "−" : "•"
                                        color: changedPathRow.modelData.kind === "added" ? app.green : changedPathRow.modelData.kind === "deleted" ? app.red : app.blue
                                        font.pixelSize: app.scaled(16)
                                        font.weight: Font.Bold
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: changedPathRow.modelData.path
                                        color: app.ink
                                        font.family: "monospace"
                                        font.pixelSize: app.scaled(11)
                                        elide: Text.ElideMiddle
                                    }
                                }
                            }
                            Label {
                                visible: app.state.review && (app.state.review.truncated || app.state.review.ignoredNoise > 0)
                                text: app.state.review ?
                                      (app.state.review.truncated ? "More paths are available in the full Snapper comparison. " : "") +
                                      (app.state.review.ignoredNoise > 0 ? app.state.review.ignoredNoise + " temporary log/cache changes were hidden as noise." : "") : ""
                                color: app.muted
                                font.pixelSize: app.scaled(11)
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: Math.max(app.scaled(310), parent.width * 0.33)
                    Layout.fillHeight: true
                    Layout.minimumHeight: timelineColumn.implicitHeight + app.scaled(40)
                    Layout.alignment: Qt.AlignTop
                    radius: app.scaled(20)
                    color: app.panel
                    border.color: app.line

                    ColumnLayout {
                        id: timelineColumn
                        anchors.fill: parent
                        anchors.margins: app.scaled(20)
                        spacing: app.scaled(12)

                        SectionLabel { text: "YOUR SYSTEM TIMELINE" }
                        Label {
                            text: "What changed, in order"
                            color: app.ink
                            font.pixelSize: app.scaled(20)
                            font.weight: Font.Bold
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "A timeline of real system checkpoints. Click a finished Rewind session to inspect it."
                            color: app.muted
                            font.pixelSize: app.scaled(12)
                            wrapMode: Text.Wrap
                        }

                        Label {
                            visible: !(app.state.sessions && app.state.sessions.length)
                            Layout.fillWidth: true
                            text: "No finished Rewind sessions yet. Your existing system snapshots still appear below."
                            color: app.muted
                            font.pixelSize: app.scaled(13)
                            wrapMode: Text.Wrap
                            topPadding: app.scaled(8)
                            bottomPadding: app.scaled(8)
                        }

                        Repeater {
                            model: (app.state.sessions || []).slice(0, 6)
                            delegate: Button {
                                id: sessionButton
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: app.scaled(67)
                                Accessible.name: "Review " + modelData.label + " from " + app.compactDate(modelData.finishedAt)
                                onClicked: app.send("REVIEW|" + modelData.pre + "|" + modelData.post)
                                contentItem: RowLayout {
                                    spacing: app.scaled(11)
                                    Rectangle {
                                        Layout.preferredWidth: app.scaled(10)
                                        Layout.preferredHeight: app.scaled(10)
                                        radius: width / 2
                                        color: app.green
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Label {
                                            Layout.fillWidth: true
                                            text: sessionButton.modelData.label
                                            color: app.ink
                                            font.pixelSize: app.scaled(13)
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }
                                        Label {
                                            text: app.compactDate(sessionButton.modelData.finishedAt)
                                            color: app.muted
                                            font.pixelSize: app.scaled(10)
                                        }
                                    }
                                    Label { text: "›"; color: app.blue; font.pixelSize: app.scaled(20) }
                                }
                                background: Rectangle {
                                    radius: app.scaled(11)
                                    color: sessionButton.down ? "#213d54" : sessionButton.hovered ? "#1b3449" : app.panelRaised
                                    border.color: sessionButton.activeFocus ? app.blue : app.line
                                    border.width: sessionButton.activeFocus ? 2 : 1
                                }
                            }
                        }

                        EmptyLine { visible: app.state.snapshots && app.state.snapshots.length > 0 }
                        SectionLabel { text: "RECENT CHECKPOINTS"; visible: app.state.snapshots && app.state.snapshots.length > 0 }

                        Repeater {
                            model: (app.state.snapshots || []).slice(0, 7)
                            delegate: RowLayout {
                                id: snapshotRow
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: app.scaled(10)
                                Rectangle {
                                    Layout.preferredWidth: app.scaled(8)
                                    Layout.preferredHeight: app.scaled(8)
                                    radius: width / 2
                                    color: snapshotRow.modelData.description.indexOf("Dagric") === 0 ? app.blue : "#62788d"
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    Label {
                                        Layout.fillWidth: true
                                        text: snapshotRow.modelData.description || "System checkpoint"
                                        color: app.ink
                                        font.pixelSize: app.scaled(11)
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: "#" + snapshotRow.modelData.number + "  " + app.compactDate(snapshotRow.modelData.date)
                                        color: app.muted
                                        font.pixelSize: app.scaled(9)
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true; Layout.minimumHeight: app.scaled(8) }
                        EmptyLine {}
                        Label {
                            Layout.fillWidth: true
                            text: "Need to go back? Rewind opens the recovery tool; it does not rewrite the live system behind your back."
                            color: app.muted
                            font.pixelSize: app.scaled(11)
                            wrapMode: Text.Wrap
                        }
                        RewindButton {
                            Layout.fillWidth: true
                            text: "Open safe recovery"
                            quiet: true
                            Accessible.name: "Open Btrfs Assistant for safe recovery"
                            onClicked: app.send("RECOVERY|")
                        }
                    }
                }
            }

            RowLayout {
                visible: app.state.ready
                Layout.fillWidth: true
                Layout.leftMargin: app.scaled(4)
                Layout.rightMargin: app.scaled(4)
                Label {
                    Layout.fillWidth: true
                    text: "Private by design: no screenshots • no cloud • no account • no document contents"
                    color: app.muted
                    font.pixelSize: app.scaled(11)
                }
                Label {
                    text: "SYSTEM CHANGES ONLY"
                    color: app.green
                    font.pixelSize: app.scaled(10)
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.8
                }
            }
        }
    }
}
