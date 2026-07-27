// SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Dagric OS — "Dagric Appearance": the preview-before-you-commit gallery.
//
// This file is the VIEW ONLY. It never touches the system: QML cannot execute
// programs, and giving it that power would make a theme picker a privilege
// problem. Instead the shell wrapper /usr/bin/dagric-appearance does every
// apply and every undo, and this window drives it over a one-way protocol:
//
//   the wrapper writes a catalogue (JSON) and passes it as --catalog=PATH
//   this window prints  @DAGRIC@<COMMAND>|<kind>|<id>  as the user clicks
//
// Commands: PREVIEW (try this one now), KEEP (stop the timer, it stays),
// REVERT (put everything back), QUIT (window closed). The wrapper reads them
// line by line. console.log() lands on stderr, which the wrapper merges into
// the same pipe, and the @DAGRIC@ marker is what separates our protocol from
// ordinary Qt chatter — so a stray warning can never be mistaken for an order.
//
// Imports are deliberately limited to QtQuick, QtQuick.Controls and
// QtQuick.Layouts: all three already ship in the Dagric image because Plasma
// itself needs them. Nothing here requires Kirigami or any KDE QML plugin, so
// the gallery still opens if a user is running a bare session.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: app

    visible: true
    width: 940
    height: 660
    minimumWidth: 460
    minimumHeight: 400
    title: "Dagric Appearance"
    color: app.cBg

    // --- brand ---------------------------------------------------------------
    readonly property color cBg: "#0a111c"
    readonly property color cSurface: "#111c2b"
    readonly property color cSurfaceHi: "#17243a"
    readonly property color cLine: "#22334d"
    readonly property color cText: "#e8eef7"
    readonly property color cDim: "#93a4bd"
    readonly property color cBrand: "#3fa9f5"

    // --- catalogue -----------------------------------------------------------
    property string edition: "free"
    property var styles: []
    property var layouts: []
    property string loadError: ""
    property bool loaded: false

    function send(msg) {
        console.log("@DAGRIC@" + msg);
    }

    function catalogPath() {
        var args = Qt.application.arguments;
        for (var i = 0; i < args.length; i++) {
            if (args[i].indexOf("--catalog=") === 0)
                return args[i].substring(10);
        }
        return "";
    }

    function loadCatalog() {
        var p = catalogPath();
        if (p === "") {
            app.loadError = "Dagric Appearance was started without a catalogue. Run it as \"dagric-appearance\" rather than opening this file directly.";
            return;
        }
        var url = (p.indexOf("file:") === 0) ? p : "file://" + encodeURI(p);
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE)
                return;
            var txt = xhr.responseText;
            if (!txt) {
                app.loadError = "The appearance catalogue could not be read.";
                return;
            }
            try {
                var data = JSON.parse(txt);
                app.edition = data.edition ? data.edition : "free";
                app.styles = data.styles ? data.styles : [];
                app.layouts = data.layouts ? data.layouts : [];
                app.loaded = true;
            } catch (e) {
                app.loadError = "The appearance catalogue is damaged.";
            }
        };
        // Qt refuses local-file XMLHttpRequest unless QML_XHR_ALLOW_FILE_READ
        // is set, and it throws rather than reporting a status. The wrapper
        // sets it; catch anyway, because a window that silently shows nothing
        // is worse than one that says what went wrong.
        try {
            xhr.open("GET", url);
            xhr.send();
        } catch (e) {
            app.loadError = "The appearance catalogue could not be read (" + e + ").";
        }
    }

    Component.onCompleted: app.loadCatalog()

    // Last resort: if the catalogue never arrives and nothing threw, say so
    // instead of leaving an empty window that looks like a missing install.
    Timer {
        interval: 4000
        running: true
        repeat: false
        onTriggered: {
            if (!app.loaded && app.loadError === "")
                app.loadError = "The appearance catalogue could not be read.";
        }
    }

    // --- preview state -------------------------------------------------------
    // Exactly one preview can be live at a time. It is never permanent: either
    // the owner presses Keep, or the countdown runs out and the wrapper puts
    // the desktop back the way it found it.
    readonly property int previewSeconds: 20
    property bool previewing: false
    property string previewKind: ""
    property string previewId: ""
    property string previewName: ""
    property int secondsLeft: 0

    function isShowing(entry) {
        return app.previewing && app.previewKind === entry.kind && app.previewId === entry.id;
    }

    function preview(entry) {
        if (app.isShowing(entry)) {
            // Clicking the tile you are already trying just buys more time.
            app.secondsLeft = app.previewSeconds;
            countdown.restart();
            return;
        }
        app.previewKind = entry.kind;
        app.previewId = entry.id;
        app.previewName = entry.name;
        app.previewing = true;
        app.secondsLeft = app.previewSeconds;
        app.send("PREVIEW|" + entry.kind + "|" + entry.id);
        countdown.restart();
    }

    function keep() {
        if (!app.previewing)
            return;
        countdown.stop();
        app.send("KEEP|" + app.previewKind + "|" + app.previewId);
        app.previewing = false;
        app.previewKind = "";
        app.previewId = "";
    }

    function revert() {
        if (!app.previewing)
            return;
        countdown.stop();
        app.send("REVERT|" + app.previewKind + "|" + app.previewId);
        app.previewing = false;
        app.previewKind = "";
        app.previewId = "";
    }

    Timer {
        id: countdown
        interval: 1000
        repeat: true
        running: false
        onTriggered: {
            app.secondsLeft = app.secondsLeft - 1;
            if (app.secondsLeft <= 0)
                app.revert();
        }
    }

    onClosing: function(close) {
        // Closing the window is not consent. Anything still on trial goes back.
        if (app.previewing)
            app.revert();
        app.send("QUIT");
    }

    Shortcut {
        sequence: "Esc"
        onActivated: {
            if (app.previewing)
                app.revert();
            else
                app.close();
        }
    }

    // --- header --------------------------------------------------------------
    header: Rectangle {
        implicitHeight: 76
        color: app.cSurface

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: app.cLine
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 14

            Rectangle {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                Layout.alignment: Qt.AlignVCenter
                radius: 11
                color: app.cBrand
                Text {
                    anchors.centerIn: parent
                    text: "D"
                    color: app.cBg
                    font.pixelSize: 23
                    font.bold: true
                }
            }

            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                Text {
                    text: "Dagric Appearance"
                    color: app.cText
                    font.pixelSize: 18
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "Click anything to try it on. Nothing is kept until you press Keep."
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
                border.color: app.cBrand
                Text {
                    id: proLabel
                    anchors.centerIn: parent
                    text: "PRO EDITION"
                    color: app.cBrand
                    font.pixelSize: 10
                    font.bold: true
                }
            }
        }
    }

    // --- one card in the grid ------------------------------------------------
    Component {
        id: cardDelegate

        Item {
            id: cell
            width: GridView.view ? GridView.view.cellWidth : 240
            height: GridView.view ? GridView.view.cellHeight : 200

            property var entry: modelData

            Rectangle {
                id: card
                anchors.fill: parent
                anchors.margins: 8
                radius: 12
                color: mouse.containsMouse ? app.cSurfaceHi : app.cSurface
                border.width: app.isShowing(cell.entry) ? 2 : 1
                border.color: app.isShowing(cell.entry) ? app.cBrand : app.cLine

                Behavior on color {
                    ColorAnimation { duration: 120 }
                }

                ColumnLayout {
                    id: cardCol
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    Item {
                        Layout.fillWidth: true
                        // 16:9, the shape tools/make-appearance-thumbs.sh
                        // renders (480x270), so a real thumbnail is shown
                        // whole rather than cropped.
                        Layout.preferredHeight: Math.round(cardCol.width * 0.5625)
                        clip: true

                        // The fallback always exists underneath: a tile in this
                        // entry's own accent colour. A missing thumbnail must
                        // never show up as a broken-image icon.
                        Rectangle {
                            anchors.fill: parent
                            radius: 6
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: cell.entry.accent }
                                GradientStop { position: 1.0; color: app.cBg }
                            }
                            Text {
                                anchors.centerIn: parent
                                text: (cell.entry.name && cell.entry.name.length > 0)
                                      ? cell.entry.name.charAt(0).toUpperCase() : "?"
                                color: "#ffffff"
                                opacity: 0.9
                                font.bold: true
                                font.pixelSize: Math.max(22, Math.round(parent.height * 0.42))
                            }
                        }

                        Image {
                            id: thumb
                            anchors.fill: parent
                            source: cell.entry.thumb ? cell.entry.thumb : ""
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            visible: status === Image.Ready
                        }

                        Rectangle {
                            visible: cell.entry.pro === true
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 6
                            width: proTag.implicitWidth + 12
                            height: proTag.implicitHeight + 6
                            radius: 4
                            color: app.cBg
                            opacity: 0.88
                            Text {
                                id: proTag
                                anchors.centerIn: parent
                                text: "PRO"
                                color: app.cBrand
                                font.pixelSize: 10
                                font.bold: true
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: cell.entry.name
                        color: app.cText
                        font.pixelSize: 14
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        text: cell.entry.desc
                        color: app.cDim
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        elide: Text.ElideRight
                        maximumLineCount: 2
                        verticalAlignment: Text.AlignTop
                    }
                }

                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: app.preview(cell.entry)
                }
            }
        }
    }

    // --- body ----------------------------------------------------------------
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: tabs
            Layout.fillWidth: true
            background: Rectangle { color: app.cBg }

            TabButton {
                id: tabStyles
                text: "Styles"
                background: Rectangle {
                    color: "transparent"
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: tabStyles.checked ? 3 : 1
                        color: tabStyles.checked ? app.cBrand : app.cLine
                    }
                }
                contentItem: Text {
                    text: tabStyles.text
                    color: tabStyles.checked ? app.cText : app.cDim
                    font.pixelSize: 14
                    font.bold: tabStyles.checked
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            TabButton {
                id: tabLayouts
                text: "Layouts"
                background: Rectangle {
                    color: "transparent"
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: tabLayouts.checked ? 3 : 1
                        color: tabLayouts.checked ? app.cBrand : app.cLine
                    }
                }
                contentItem: Text {
                    text: tabLayouts.text
                    color: tabLayouts.checked ? app.cText : app.cDim
                    font.pixelSize: 14
                    font.bold: tabLayouts.checked
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            Item {
                GridView {
                    id: styleGrid
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    visible: app.styles.length > 0
                    model: app.styles
                    delegate: cardDelegate
                    cacheBuffer: 600

                    property int columns: Math.max(1, Math.floor(width / 250))
                    cellWidth: Math.floor(width / columns)
                    cellHeight: Math.round((cellWidth - 36) * 0.5625) + 104

                    ScrollBar.vertical: ScrollBar {
                        contentItem: Rectangle {
                            implicitWidth: 6
                            radius: 3
                            color: app.cLine
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 60
                    visible: app.styles.length === 0
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: app.cDim
                    font.pixelSize: 13
                    text: app.loadError !== ""
                          ? app.loadError
                          : "No styles are installed. Reinstall the dagric-branding package to restore them."
                }
            }

            Item {
                GridView {
                    id: layoutGrid
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    visible: app.layouts.length > 0
                    model: app.layouts
                    delegate: cardDelegate
                    cacheBuffer: 600

                    property int columns: Math.max(1, Math.floor(width / 250))
                    cellWidth: Math.floor(width / columns)
                    cellHeight: Math.round((cellWidth - 36) * 0.5625) + 104

                    ScrollBar.vertical: ScrollBar {
                        contentItem: Rectangle {
                            implicitWidth: 6
                            radius: 3
                            color: app.cLine
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 60
                    visible: app.layouts.length === 0
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: app.cDim
                    font.pixelSize: 13
                    text: app.loadError !== ""
                          ? app.loadError
                          : "No layouts are installed. Reinstall the dagric-branding package to restore them."
                }
            }
        }
    }

    // --- the preview bar -----------------------------------------------------
    // The whole point of this application. It stays on screen for as long as
    // something is on trial, and it never lies about what happens next.
    footer: Rectangle {
        id: bar
        visible: app.previewing
        implicitHeight: app.previewing ? 72 : 0
        color: "#132338"

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 2
            color: app.cBrand
        }

        RowLayout {
            anchors.fill: parent
            anchors.topMargin: 2
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 16
            visible: app.previewing

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                Text {
                    Layout.fillWidth: true
                    text: "Previewing " + app.previewName
                    color: app.cText
                    font.pixelSize: 15
                    font.bold: true
                    elide: Text.ElideRight
                }

                RowLayout {
                    spacing: 10
                    Text {
                        text: app.secondsLeft === 1
                              ? "Reverting in 1 second"
                              : "Reverting in " + app.secondsLeft + " seconds"
                        color: app.cDim
                        font.pixelSize: 12
                    }
                    Rectangle {
                        Layout.preferredWidth: 110
                        Layout.preferredHeight: 5
                        Layout.alignment: Qt.AlignVCenter
                        radius: 3
                        color: app.cLine
                        Rectangle {
                            height: parent.height
                            radius: 3
                            color: app.cBrand
                            width: parent.width * Math.max(0, Math.min(1, app.secondsLeft / app.previewSeconds))
                            Behavior on width {
                                NumberAnimation { duration: 280 }
                            }
                        }
                    }
                }
            }

            Button {
                id: revertBtn
                text: "Revert"
                Layout.preferredHeight: 36
                Layout.preferredWidth: 104
                onClicked: app.revert()
                background: Rectangle {
                    radius: 8
                    color: revertBtn.down ? "#1b2c44" : "transparent"
                    border.width: 1
                    border.color: app.cLine
                }
                contentItem: Text {
                    text: revertBtn.text
                    color: app.cText
                    font.pixelSize: 13
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Button {
                id: keepBtn
                text: "Keep"
                Layout.preferredHeight: 36
                Layout.preferredWidth: 104
                onClicked: app.keep()
                background: Rectangle {
                    radius: 8
                    color: keepBtn.down ? "#2f8ed0" : app.cBrand
                }
                contentItem: Text {
                    text: keepBtn.text
                    color: app.cBg
                    font.pixelSize: 13
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
