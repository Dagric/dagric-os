// SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Dagric OS — "Set Up Dagric": the first-run wizard.
//
// This file is the VIEW ONLY. It never touches the system: QML cannot execute
// programs, and a wizard that could would be a privilege problem rather than a
// convenience. The shell wrapper /usr/bin/dagric-firstrun does every apply and
// every undo, and this window drives it over a one-way protocol:
//
//   the wrapper writes a catalogue (JSON) and passes it as --catalog=PATH
//   this window prints  @DAGRIC@<COMMAND>|<argument>  as the owner clicks
//
// console.log() lands on stderr, which the wrapper merges into the same pipe,
// and the @DAGRIC@ marker is what separates our protocol from ordinary Qt
// chatter — so a stray warning can never be mistaken for an order.
//
// WHAT MAKES IT A WIZARD AND NOT A FORM. Nothing is queued up and applied at
// the end: every click applies FOR REAL and immediately, the desktop behind
// changes, and this window repaints itself in the colours being chosen. The
// owner is never asked to imagine the result. That instant payoff is the whole
// reason the appearance step comes second, before anything abstract.
//
// The steps are built at runtime from what the machine can actually do — a
// page whose answer is already known, or whose button could not work here, is
// a page that teaches the owner their choices do not matter. So the migration
// step only exists when a Windows drive was found, and the text-size step only
// exists when the text size can actually be set.
//
// Imports are deliberately limited to QtQuick, QtQuick.Controls and
// QtQuick.Layouts: all three ship in the Dagric image because Plasma itself
// needs them. Nothing here needs Kirigami or any KDE QML plugin, so the wizard
// still opens in a bare session.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: app

    visible: true
    width: 1060
    height: 720
    minimumWidth: 760
    minimumHeight: 560
    title: "Set Up Dagric"
    color: app.cBg

    // --- the catalogue -------------------------------------------------------
    property string edition: "free"
    property string editionName: "Dagric OS"
    property bool live: false
    property string scaleMode: "none"      // wayland | x11 | none
    property int currentScale: 0
    property bool hasDisplayTool: false
    property bool hasWindows: false
    property var wallpapers: []
    property var accents: []
    property var layouts: []
    property string loadError: ""
    property bool loaded: false

    // --- what the owner has chosen -------------------------------------------
    property string mode: "light"
    property string accentId: ""
    property string wallId: ""
    property int scale: 0
    property string layoutId: ""
    property bool changed: false
    property var touched: ({})

    // --- brand ---------------------------------------------------------------
    // The window wears the theme being chosen. Clicking "Dark" is supposed to
    // feel like flipping a switch on the whole machine, and a wizard that stays
    // stubbornly light while the desktop behind it goes dark undercuts that.
    readonly property bool dark: app.mode === "dark"
    property color cBg:     app.dark ? "#0a111c" : "#eef2f8"
    property color cPanel:  app.dark ? "#111c2b" : "#ffffff"
    property color cPanel2: app.dark ? "#17243a" : "#e3eaf4"
    property color cLine:   app.dark ? "#22334d" : "#cfd9e8"
    property color cText:   app.dark ? "#e8eef7" : "#101a26"
    property color cDim:    app.dark ? "#93a4bd" : "#586a80"
    property color cAccent: "#3fa9f5"
    readonly property color cOnAccent: app.dark ? "#0a111c" : "#ffffff"

    Behavior on cBg     { ColorAnimation { duration: 200 } }
    Behavior on cPanel  { ColorAnimation { duration: 200 } }
    Behavior on cPanel2 { ColorAnimation { duration: 200 } }
    Behavior on cLine   { ColorAnimation { duration: 200 } }
    Behavior on cText   { ColorAnimation { duration: 200 } }
    Behavior on cDim    { ColorAnimation { duration: 200 } }
    Behavior on cAccent { ColorAnimation { duration: 200 } }

    function send(msg) {
        console.log("@DAGRIC@" + msg);
    }

    // --- loading -------------------------------------------------------------
    function catalogPath() {
        var args = Qt.application.arguments;
        for (var i = 0; i < args.length; i++) {
            if (args[i].indexOf("--catalog=") === 0)
                return args[i].substring(10);
        }
        return "";
    }

    function loadCatalog() {
        var p = app.catalogPath();
        if (p === "") {
            app.loadError = "Set Up Dagric was started without a catalogue. Run it as \"dagric-firstrun\" rather than opening this file directly.";
            return;
        }
        var url = (p.indexOf("file:") === 0) ? p : "file://" + encodeURI(p);
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE)
                return;
            var txt = xhr.responseText;
            if (!txt) {
                app.loadError = "The setup catalogue could not be read.";
                return;
            }
            try {
                var d = JSON.parse(txt);
                app.edition = d.edition ? d.edition : "free";
                app.editionName = d.editionName ? d.editionName : "Dagric OS";
                app.live = d.live === true;
                app.scaleMode = d.scaleMode ? d.scaleMode : "none";
                app.currentScale = d.currentScale ? d.currentScale : 0;
                app.hasDisplayTool = d.hasDisplayTool === true;
                app.hasWindows = d.hasWindows === true;
                app.wallpapers = d.wallpapers ? d.wallpapers : [];
                app.accents = d.accents ? d.accents : [];
                app.layouts = d.layouts ? d.layouts : [];
                // Start from what is already on screen, so the tiles show the
                // truth on arrival rather than pretending nothing is set.
                app.mode = (d.currentMode === "dark") ? "dark" : "light";
                app.wallId = d.currentWall ? d.currentWall : "";
                app.scale = app.currentScale;
                app.loaded = true;
                app.buildSteps();
            } catch (e) {
                app.loadError = "The setup catalogue is damaged.";
            }
        };
        // Qt refuses local-file XMLHttpRequest unless QML_XHR_ALLOW_FILE_READ is
        // set, and it throws rather than reporting a status. The wrapper sets
        // it; catch anyway, because a window that silently shows nothing is
        // worse than one that says what went wrong.
        try {
            xhr.open("GET", url);
            xhr.send();
        } catch (e) {
            app.loadError = "The setup catalogue could not be read (" + e + ").";
        }
    }

    Component.onCompleted: {
        app.loadCatalog();
        // FIT THE SCREEN BEFORE CENTRING ON IT. 1060x720 is the comfortable
        // size, but it was being used as the only size: on anything narrower
        // the window simply hung off the right-hand edge, and the right-hand
        // edge is where the footer keeps "Next" — the one control the owner
        // has to reach. That is not a corner case here. A cautious Windows
        // refugee tries the live ISO in VirtualBox or Boxes first, and those
        // open at 800x600 or 1024x768; so does many an old 4:3 monitor on the
        // machine being rescued. Shrink to what the screen actually offers,
        // never below the minimum the layout needs, and use the AVAILABLE
        // geometry so we do not centre the footer underneath the taskbar.
        var aw = Screen.desktopAvailableWidth  > 0 ? Screen.desktopAvailableWidth  : Screen.width;
        var ah = Screen.desktopAvailableHeight > 0 ? Screen.desktopAvailableHeight : Screen.height;
        app.width  = Math.max(app.minimumWidth,  Math.min(app.width,  aw - 40));
        app.height = Math.max(app.minimumHeight, Math.min(app.height, ah - 40));
        app.x = Math.max(0, Math.round((aw - app.width) / 2));
        app.y = Math.max(0, Math.round((ah - app.height) / 2));
        // The wrapper writes its "already shown" stamp on this line and not a
        // moment earlier: if the session was not ready and we never got here,
        // the next login must try again instead of losing the only chance.
        app.send("READY");
    }

    // Last resort: if the catalogue never arrives and nothing threw, say so
    // rather than leaving an empty window that looks like a broken install.
    Timer {
        interval: 4000
        running: true
        repeat: false
        onTriggered: {
            if (!app.loaded && app.loadError === "")
                app.loadError = "The setup catalogue could not be read.";
        }
    }

    // --- the steps -----------------------------------------------------------
    property var steps: ["welcome", "finish"]
    property int stepIndex: 0
    readonly property string step: (app.stepIndex >= 0 && app.stepIndex < app.steps.length)
                                   ? app.steps[app.stepIndex] : "welcome"

    function buildSteps() {
        var s = ["welcome"];
        if (app.wallpapers.length > 0 || app.accents.length > 0)
            s.push("appearance");
        // Only offer a text size when there is a mechanism to set one. On a
        // session where neither kscreen-doctor nor the X11 keys are usable,
        // three buttons that quietly do nothing are worse than no step at all.
        if (app.hasDisplayTool || app.scaleMode !== "none")
            s.push("display");
        if (app.layouts.length > 0)
            s.push("taskbar");
        if (app.hasWindows && !app.live)
            s.push("files");
        s.push("finish");
        app.steps = s;
        app.stepIndex = 0;
    }

    function stepTitle(id) {
        switch (id) {
        case "welcome":    return "Welcome";
        case "appearance": return "How it looks";
        case "display":    return "Text size";
        case "taskbar":    return "The taskbar";
        case "files":      return "Your files";
        case "finish":     return "You're ready";
        }
        return id;
    }

    function isTouched(id) { return app.touched[id] === true; }

    function markTouched(id) {
        var t = app.touched;
        t[id] = true;
        app.touched = t;      // reassign: QML does not see in-place edits
        app.changed = true;
    }

    function goNext() {
        if (app.stepIndex < app.steps.length - 1)
            app.stepIndex = app.stepIndex + 1;
        else
            app.finish();
    }

    function goBack() {
        if (app.stepIndex > 0)
            app.stepIndex = app.stepIndex - 1;
    }

    function finish() {
        app.send("DONE");
        app.finished = true;
        app.close();
    }

    property bool finished: false

    // --- choices -------------------------------------------------------------
    function pickMode(m) {
        if (m !== "light" && m !== "dark")
            return;
        app.mode = m;
        app.markTouched("appearance");
        app.send("MODE|" + m);
    }

    function pickAccent(a) {
        app.accentId = a.id;
        app.cAccent = a.hex;
        app.markTouched("appearance");
        app.send("ACCENT|" + a.id);
    }

    function pickWall(w) {
        app.wallId = w.id;
        app.markTouched("appearance");
        app.send("WALL|" + w.id);
    }

    function pickScale(v) {
        app.scale = v;
        app.markTouched("display");
        app.send("SCALE|" + v);
    }

    function pickLayout(l) {
        app.layoutId = l.id;
        app.markTouched("taskbar");
        app.send("LAYOUT|" + l.id);
    }

    function run(what) {
        app.send("RUN|" + what);
    }

    function undoAll() {
        app.send("UNDO");
        app.changed = false;
        app.touched = ({});
        app.accentId = "";
        app.layoutId = "";
        app.cAccent = "#3fa9f5";
    }

    onClosing: function(close) {
        // Closing early is an answer, not a failure. Nothing is rolled back:
        // every choice was applied whole, so what is on screen is a desktop
        // that works — and "Undo my changes" was on offer the entire time.
        if (!app.finished)
            app.send("QUIT");
    }

    Shortcut {
        sequence: "Esc"
        onActivated: app.close()
    }

    // =========================================================== small pieces
    component Primary: Button {
        id: pb
        implicitHeight: 40
        implicitWidth: Math.max(120, pbText.implicitWidth + 44)
        background: Rectangle {
            radius: 9
            color: pb.down ? Qt.darker(app.cAccent, 1.25)
                           : (pb.hovered ? Qt.lighter(app.cAccent, 1.08) : app.cAccent)
        }
        contentItem: Text {
            id: pbText
            text: pb.text
            color: app.cOnAccent
            font.pixelSize: 14
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component Ghost: Button {
        id: gb
        implicitHeight: 40
        implicitWidth: Math.max(110, gbText.implicitWidth + 40)
        background: Rectangle {
            radius: 9
            color: gb.down ? app.cPanel2 : "transparent"
            border.width: 1
            border.color: app.cLine
        }
        contentItem: Text {
            id: gbText
            text: gb.text
            color: app.cText
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component Quiet: Button {
        id: qb
        implicitHeight: 34
        implicitWidth: qbText.implicitWidth + 18
        background: Item {}
        contentItem: Text {
            id: qbText
            text: qb.text
            color: qb.hovered ? app.cText : app.cDim
            font.pixelSize: 13
            font.underline: qb.hovered
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    // A page heading. Every step gets the same shape so the wizard reads as one
    // thing rather than six screens that happened to end up next to each other.
    // The root carries an id and the children use it: "parent" would also work
    // today, but it silently means something else the moment a wrapper item is
    // added, and this is the kind of breakage that shows up as a blank heading
    // on somebody's first boot rather than as a build error.
    component PageHead: ColumnLayout {
        id: ph
        property string heading: ""
        property string sub: ""
        Layout.fillWidth: true
        spacing: 6
        Text {
            Layout.fillWidth: true
            text: ph.heading
            color: app.cText
            font.pixelSize: 27
            font.bold: true
            wrapMode: Text.WordWrap
        }
        Text {
            Layout.fillWidth: true
            text: ph.sub
            visible: text !== ""
            color: app.cDim
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }

    // A selectable card. Used for light/dark, text size and the finish links.
    component Choice: Rectangle {
        id: ch
        property bool selected: false
        signal clicked()
        radius: 12
        color: chMouse.containsMouse ? app.cPanel2 : app.cPanel
        border.width: ch.selected ? 2 : 1
        border.color: ch.selected ? app.cAccent : app.cLine
        Behavior on color { ColorAnimation { duration: 120 } }
        MouseArea {
            id: chMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: ch.clicked()
        }
    }

    // A miniature desktop, painted live in the colours currently chosen. It is
    // what makes "Light" and "Dark" a picture instead of a word.
    component MiniDesktop: Item {
        id: md
        property bool useDark: false
        property color accent: app.cAccent
        readonly property color mBg:    md.useDark ? "#0d1726" : "#dbe4f0"
        readonly property color mWin:   md.useDark ? "#16233a" : "#ffffff"
        readonly property color mEdge:  md.useDark ? "#27395a" : "#c6d2e4"
        readonly property color mPanel: md.useDark ? "#0a111c" : "#f2f6fc"

        Rectangle {
            anchors.fill: parent
            radius: 7
            clip: true
            color: md.mBg

            Rectangle {                                    // a window
                x: parent.width * 0.16
                y: parent.height * 0.16
                width: parent.width * 0.68
                height: parent.height * 0.52
                radius: 4
                color: md.mWin
                border.width: 1
                border.color: md.mEdge

                Rectangle {                                // its titlebar
                    id: mdTitle
                    width: parent.width
                    height: Math.max(6, parent.height * 0.28)
                    radius: 4
                    color: md.accent
                    Rectangle {                            // square off the bottom
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: mdTitle.radius
                        color: md.accent
                    }
                }
            }

            Rectangle {                                    // the panel
                anchors.bottom: parent.bottom
                width: parent.width
                height: Math.max(7, parent.height * 0.17)
                color: md.mPanel
                Rectangle {                                // the launcher button
                    x: 4
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(6, parent.height * 0.66)
                    height: width
                    radius: 2
                    color: md.accent
                }
            }
        }
    }

    // ================================================================= header
    header: Rectangle {
        implicitHeight: 74
        color: app.cPanel

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: app.cLine
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 22
            anchors.rightMargin: 18
            spacing: 14

            Rectangle {
                Layout.preferredWidth: 38
                Layout.preferredHeight: 38
                Layout.alignment: Qt.AlignVCenter
                radius: 11
                color: app.cAccent
                Text {
                    anchors.centerIn: parent
                    text: "D"
                    color: app.cOnAccent
                    font.pixelSize: 22
                    font.bold: true
                }
            }

            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                Text {
                    text: "Set Up Dagric"
                    color: app.cText
                    font.pixelSize: 17
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "Every step can be skipped, and you can change all of it later."
                    color: app.cDim
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }

            Rectangle {
                visible: app.edition === "pro"
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: proLabel.implicitWidth + 18
                Layout.preferredHeight: 24
                radius: 12
                color: "transparent"
                border.width: 1
                border.color: app.cAccent
                Text {
                    id: proLabel
                    anchors.centerIn: parent
                    text: "PRO EDITION"
                    color: app.cAccent
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            Quiet {
                text: "Undo my changes"
                visible: app.changed
                Layout.alignment: Qt.AlignVCenter
                onClicked: app.undoAll()
            }

            Quiet {
                text: "I'll do this later"
                Layout.alignment: Qt.AlignVCenter
                onClicked: app.close()
            }
        }
    }

    // =================================================================== body
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // --- the rail: where am I, and how much is left ----------------------
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 218
            visible: app.width >= 900
            color: app.cPanel

            Rectangle {
                anchors.right: parent.right
                height: parent.height
                width: 1
                color: app.cLine
            }

            ColumnLayout {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: 24
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                spacing: 4

                Repeater {
                    model: app.steps
                    delegate: RowLayout {
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        spacing: 11

                        Rectangle {
                            Layout.preferredWidth: 26
                            Layout.preferredHeight: 26
                            radius: 13
                            color: index === app.stepIndex ? app.cAccent
                                 : (index < app.stepIndex ? app.cPanel2 : "transparent")
                            border.width: index > app.stepIndex ? 1 : 0
                            border.color: app.cLine
                            Text {
                                anchors.centerIn: parent
                                text: index < app.stepIndex ? "✓" : (index + 1)
                                color: index === app.stepIndex ? app.cOnAccent
                                     : (index < app.stepIndex ? app.cAccent : app.cDim)
                                font.pixelSize: 13
                                font.bold: true
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            text: app.stepTitle(modelData)
                            color: index === app.stepIndex ? app.cText : app.cDim
                            font.pixelSize: 14
                            font.bold: index === app.stepIndex
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }

            Text {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 18
                text: app.live
                      ? "Live trial — anything you set here lasts until you shut down."
                      : app.editionName
                color: app.cDim
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
        }

        // --- the page --------------------------------------------------------
        Item {
            id: pageArea
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Something went wrong loading the catalogue: say what, plainly,
            // instead of showing an empty wizard that looks like a bad build.
            Text {
                anchors.centerIn: parent
                width: parent.width - 90
                visible: app.loadError !== ""
                text: app.loadError
                color: app.cDim
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            // ------------------------------------------------------- welcome
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                spacing: 0
                visible: app.step === "welcome" && app.loadError === ""

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.preferredWidth: 88
                    Layout.preferredHeight: 88
                    radius: 24
                    color: app.cAccent
                    Text {
                        anchors.centerIn: parent
                        text: "D"
                        color: app.cOnAccent
                        font.pixelSize: 52
                        font.bold: true
                    }
                }

                Item { Layout.preferredHeight: 26 }

                Text {
                    Layout.fillWidth: true
                    text: "Welcome to " + app.editionName + "."
                    color: app.cText
                    font.pixelSize: 34
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Item { Layout.preferredHeight: 12 }

                Text {
                    Layout.fillWidth: true
                    Layout.maximumWidth: 560
                    text: "Let's make it yours. A few minutes now — the colours, the "
                        + "wallpaper, how big the text is, where the taskbar sits"
                        + (app.hasWindows ? ", and your files from Windows" : "")
                        + " — and then it's out of your way."
                    color: app.cDim
                    font.pixelSize: 16
                    lineHeight: 1.35
                    wrapMode: Text.WordWrap
                }

                Item { Layout.preferredHeight: 18 }

                Text {
                    Layout.fillWidth: true
                    Layout.maximumWidth: 560
                    text: app.live
                          ? "You're running the live trial from the USB stick, so anything you set here lasts until you shut down. Install Dagric first if you want it to stick."
                          : "Nothing here is permanent. Skip anything you like, and change all of it later from the Dagric Hub."
                    color: app.cDim
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }

                Item { Layout.fillHeight: true }
            }

            // ---------------------------------------------------- appearance
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 34
                spacing: 18
                visible: app.step === "appearance" && app.loadError === ""

                PageHead {
                    heading: "Pick a look."
                    sub: "Click anything — the desktop behind this window changes as you go."
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    Choice {
                        Layout.preferredWidth: 178
                        Layout.preferredHeight: 108
                        selected: app.mode === "light"
                        onClicked: app.pickMode("light")
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 7
                            MiniDesktop {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                useDark: false
                            }
                            Text {
                                text: "Light"
                                color: app.cText
                                font.pixelSize: 13
                                font.bold: true
                            }
                        }
                    }

                    Choice {
                        Layout.preferredWidth: 178
                        Layout.preferredHeight: 108
                        selected: app.mode === "dark"
                        onClicked: app.pickMode("dark")
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 7
                            MiniDesktop {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                useDark: true
                            }
                            Text {
                                text: "Dark"
                                color: app.cText
                                font.pixelSize: 13
                                font.bold: true
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        Layout.topMargin: 6
                        spacing: 9
                        visible: app.accents.length > 0

                        Text {
                            text: "Highlight colour"
                            color: app.cDim
                            font.pixelSize: 13
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 9
                            Repeater {
                                model: app.accents
                                delegate: Rectangle {
                                    required property var modelData
                                    width: 32
                                    height: 32
                                    radius: 16
                                    color: modelData.hex
                                    border.width: app.accentId === modelData.id ? 3 : 1
                                    border.color: app.accentId === modelData.id
                                                  ? app.cText : app.cLine
                                    // "Theme default" is not a colour of its own;
                                    // mark it so it does not read as plain blue.
                                    Text {
                                        anchors.centerIn: parent
                                        visible: modelData.id === "default"
                                        text: "✦"
                                        color: "#ffffff"
                                        font.pixelSize: 14
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        ToolTip.visible: containsMouse
                                        ToolTip.text: modelData.name
                                        onClicked: app.pickAccent(modelData)
                                    }
                                }
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: 2
                    text: "Wallpaper"
                    color: app.cDim
                    font.pixelSize: 13
                    visible: app.wallpapers.length > 0
                }

                GridView {
                    id: wallGrid
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    visible: app.wallpapers.length > 0
                    model: app.wallpapers
                    cacheBuffer: 800

                    property int columns: Math.max(2, Math.floor(width / 190))
                    cellWidth: Math.floor(width / columns)
                    cellHeight: Math.round((cellWidth - 14) * 0.5625) + 30

                    ScrollBar.vertical: ScrollBar {
                        contentItem: Rectangle {
                            implicitWidth: 6
                            radius: 3
                            color: app.cLine
                        }
                    }

                    delegate: Item {
                        id: wcell
                        required property var modelData
                        width: GridView.view ? GridView.view.cellWidth : 180
                        height: GridView.view ? GridView.view.cellHeight : 120

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 6
                            radius: 9
                            color: "transparent"
                            border.width: app.wallId === wcell.modelData.id ? 2 : 1
                            border.color: app.wallId === wcell.modelData.id
                                          ? app.cAccent
                                          : (wmouse.containsMouse ? app.cDim : app.cLine)

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 3

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true

                                    // Underneath always: a flat tile, so a
                                    // wallpaper that fails to decode shows as a
                                    // blank card and never a broken-image icon.
                                    Rectangle {
                                        anchors.fill: parent
                                        radius: 6
                                        color: app.cPanel2
                                    }

                                    Image {
                                        anchors.fill: parent
                                        source: wcell.modelData.thumb
                                        fillMode: Image.PreserveAspectCrop
                                        asynchronous: true
                                        visible: status === Image.Ready
                                        // These are the real 1920x1080 shipped
                                        // wallpapers, not separate thumbnails —
                                        // one set of files, and a wallpaper
                                        // added later needs nothing regenerated.
                                        // sourceSize is what keeps that cheap:
                                        // Qt retains the scaled image, so a tile
                                        // costs ~0.3 MB instead of 8 MB.
                                        sourceSize.width: 380
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: wcell.modelData.name
                                    color: app.wallId === wcell.modelData.id
                                           ? app.cText : app.cDim
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    horizontalAlignment: Text.AlignHCenter
                                }
                            }

                            MouseArea {
                                id: wmouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: app.pickWall(wcell.modelData)
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: "Want your own picture? Right-click the desktop and choose Configure Desktop."
                    color: app.cDim
                    font.pixelSize: 11
                }
            }

            // ------------------------------------------------------- display
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                spacing: 20
                visible: app.step === "display" && app.loadError === ""

                PageHead {
                    heading: "Is the text the right size?"
                    sub: app.hasDisplayTool
                         ? "Dagric guessed from your screen. Open Display Settings if it guessed wrong."
                         : (app.scaleMode === "x11"
                            ? "Dagric guessed from your screen. A change here takes effect the next time you sign in."
                            : "Dagric guessed from your screen. Pick another size and it changes right away.")
                }

                // The dedicated tool owns this properly when it is installed —
                // shipping a second, disagreeing text-size control would just
                // give support two answers to the same question.
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    visible: app.hasDisplayTool

                    Primary {
                        text: "Open Display Settings"
                        onClicked: { app.markTouched("display"); app.run("display"); }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    visible: !app.hasDisplayTool

                    Repeater {
                        model: [
                            { v: 100, name: "Normal",  note: "Standard size" },
                            { v: 125, name: "Bigger",  note: "Easier to read" },
                            { v: 150, name: "Biggest", note: "Large text" }
                        ]
                        delegate: Choice {
                            required property var modelData
                            implicitWidth: 176
                            implicitHeight: 132
                            selected: app.scale === modelData.v
                            onClicked: app.pickScale(modelData.v)
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 4
                                Text {
                                    text: "Aa"
                                    color: app.cText
                                    // Draw the sizes at their real ratio, so the
                                    // card shows the answer instead of naming it.
                                    font.pixelSize: Math.round(22 * modelData.v / 100)
                                    font.bold: true
                                }
                                Item { Layout.fillHeight: true }
                                Text {
                                    text: modelData.name + "  " + modelData.v + "%"
                                    color: app.cText
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                                Text {
                                    text: modelData.note
                                    color: app.cDim
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: "You can change this again in System Settings ▸ Display & Monitor."
                    color: app.cDim
                    font.pixelSize: 12
                }
            }

            // ------------------------------------------------------- taskbar
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 34
                spacing: 16
                visible: app.step === "taskbar" && app.loadError === ""

                PageHead {
                    heading: "Where should the taskbar go?"
                    sub: "Click one to try it. Your open windows and apps stay exactly where they are."
                }

                GridView {
                    id: layoutGrid
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: app.layouts
                    cacheBuffer: 800

                    property int columns: Math.max(2, Math.floor(width / 250))
                    cellWidth: Math.floor(width / columns)
                    // Room for the picture, the name, and TWO lines of the
                    // description. One line elided "a taskbar at the bottom,
                    // familiar and c…" — which cuts the sentence exactly where
                    // it was about to say the reassuring part.
                    cellHeight: Math.round((cellWidth - 24) * 0.5625) + 78

                    ScrollBar.vertical: ScrollBar {
                        contentItem: Rectangle {
                            implicitWidth: 6
                            radius: 3
                            color: app.cLine
                        }
                    }

                    delegate: Item {
                        id: lcell
                        required property var modelData
                        width: GridView.view ? GridView.view.cellWidth : 240
                        height: GridView.view ? GridView.view.cellHeight : 180

                        Choice {
                            anchors.fill: parent
                            anchors.margins: 7
                            selected: app.layoutId === lcell.modelData.id
                            onClicked: app.pickLayout(lcell.modelData)

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 7

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    Rectangle {
                                        anchors.fill: parent
                                        radius: 6
                                        color: app.cPanel2
                                    }
                                    Image {
                                        anchors.fill: parent
                                        source: lcell.modelData.thumb
                                        fillMode: Image.PreserveAspectCrop
                                        asynchronous: true
                                        visible: status === Image.Ready
                                        sourceSize.width: 420
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: lcell.modelData.name
                                    color: app.cText
                                    font.pixelSize: 13
                                    font.bold: true
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: lcell.modelData.desc
                                    color: app.cDim
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }

            // --------------------------------------------------------- files
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                spacing: 18
                visible: app.step === "files" && app.loadError === ""

                PageHead {
                    heading: "Bring your files across."
                    sub: "There's a Windows drive in this PC. Dagric can copy your Documents, Pictures, Music, Videos, Downloads and browser bookmarks over."
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.maximumWidth: 640
                    Layout.preferredHeight: contentCol.implicitHeight + 34
                    radius: 12
                    color: app.cPanel
                    border.width: 1
                    border.color: app.cLine

                    ColumnLayout {
                        id: contentCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 17
                        spacing: 8
                        Text {
                            Layout.fillWidth: true
                            text: "Windows is only ever READ."
                            color: app.cText
                            font.pixelSize: 14
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: "Nothing on the Windows drive is moved, changed or deleted, "
                                + "and files already here are never overwritten. If you change "
                                + "your mind about Dagric, Windows is exactly as you left it."
                            color: app.cDim
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Primary {
                        text: "Bring my files over"
                        onClicked: { app.markTouched("files"); app.run("migrate"); }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "This opens in its own window — carry on here while it works."
                        color: app.cDim
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: "Not now? It's in the Dagric Hub under \"Migrate from Windows\", any time."
                    color: app.cDim
                    font.pixelSize: 12
                }
            }

            // -------------------------------------------------------- finish
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                spacing: 18
                visible: app.step === "finish" && app.loadError === ""

                PageHead {
                    heading: "That's it — " + app.editionName + " is yours."
                    sub: "Four places worth knowing about. Everything else you can find by pressing the launcher and typing."
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    // "guide" and "manual" are two different documents and the
                    // cards have to say so, because an owner who opens the
                    // wrong one and finds nothing about their printer concludes
                    // Dagric has no help. Guide = your first week. Manual = a
                    // page per application, offline, searchable by the Windows
                    // name you already know.
                    Repeater {
                        model: [
                            { act: "hub",     title: "Dagric Hub",
                              body: "Drivers, setup, security and migration, all in one menu." },
                            { act: "guide",   title: "User Guide",
                              body: "Your first week: updates, printers, Wi-Fi, shortcuts." },
                            { act: "manual",  title: "App Manual",
                              body: "A page on every app, and what it replaced on Windows." },
                            { act: "welcome", title: "Welcome page",
                              body: "What Dagric is, and the promises it makes." }
                        ]
                        delegate: Choice {
                            required property var modelData
                            Layout.fillWidth: true
                            // 146 was sized for three cards. Four share the
                            // same row, so each is ~2/3 as wide and every body
                            // line wraps sooner; the extra 24px is what keeps
                            // the "Open →" line on screen at minimumWidth 760.
                            Layout.preferredHeight: 170
                            onClicked: app.run(modelData.act)
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.title
                                    color: app.cText
                                    font.pixelSize: 15
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                }
                                Text {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: modelData.body
                                    color: app.cDim
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    verticalAlignment: Text.AlignTop
                                }
                                Text {
                                    text: "Open  →"
                                    color: app.cAccent
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: app.live
                          ? "This is the live trial. To keep any of it, run Install Dagric OS from the desktop."
                          : "Want to run through this again? It's called \"Set Up Dagric\" in your apps list."
                    color: app.cDim
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    // ================================================================= footer
    footer: Rectangle {
        implicitHeight: 74
        color: app.cPanel

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: app.cLine
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 22
            anchors.rightMargin: 22
            spacing: 12

            Ghost {
                text: "Back"
                visible: app.stepIndex > 0
                onClicked: app.goBack()
            }

            Item { Layout.fillWidth: true }

            // Only offered while this step is still unanswered. Once something
            // here has been clicked there is nothing left to skip, and two
            // buttons that do the same thing is a puzzle, not a choice.
            Quiet {
                text: "Skip this step"
                visible: app.step !== "welcome" && app.step !== "finish"
                         && !app.isTouched(app.step)
                onClicked: app.goNext()
            }

            Primary {
                text: app.step === "finish" ? "Finish"
                    : (app.step === "welcome" ? "Let's go" : "Next")
                onClicked: app.goNext()
            }
        }
    }
}
