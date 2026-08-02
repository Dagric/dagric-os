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
//
// ============================================================ ACCESSIBILITY
//
// Same story as the first-run wizard, and the same three root causes: the
// cards were bare Rectangles with a MouseArea, so they had no accessible role
// (Qt builds no accessible object without one), they were not in the Tab chain
// (Item.activeFocusOnTab defaults to false), and a MouseArea offers assistive
// technology no way to press anything. The two tabs at the top were the only
// keyboard-reachable controls in the whole application: you could switch
// between Styles and Layouts and then do absolutely nothing with either.
//
// Two problems are specific to THIS window, and both are more serious than
// they look:
//
//  1. THE COUNTDOWN WAS A TIMING FAILURE. Twenty seconds to read a bar and
//     press Keep is fine if you can see it. If Orca has to speak the bar
//     first, and you then have to Tab to find the button, twenty seconds is
//     not enough — and when it runs out your choice is silently thrown away.
//     WCAG 2.2.1 Timing Adjustable is Level A, and its "essential" exception
//     does not cover this: letting the user ask for longer does not break the
//     safety net, it only delays it. Hence "More time", which adds twenty
//     seconds as often as it is pressed, and the spoken warnings at ten and
//     five seconds so nobody is surprised by the revert.
//
//  2. THE BAR APPEARS OUT OF NOWHERE. A sighted user sees a bar slide in. A
//     screen-reader user got silence, then twenty seconds later the desktop
//     changed back for no stated reason. It now announces itself, assertively,
//     because this one really is urgent — but it still does NOT steal focus,
//     so somebody arrowing through the gallery is not yanked out of it.
//
// The negative rule from the wizard applies here too: never move focus on a
// timer, never re-focus on a value change. The countdown speaks; it does not
// grab.

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

    // --- honouring the desktop's own text size -------------------------------
    // See the long note in firstrun/main.qml: EN 301 549 11.7 and Section 508
    // 503.2 require an application to permit the platform's own font-size
    // preference, and every size in this file used to be a hard number. A
    // FontMetrics with no font of its own reports the real application font,
    // so ~15px tall is an ordinary desktop and anything larger scales the
    // window with it. At the default this is exactly 1.0 and nothing moves.
    FontMetrics { id: sysFont }
    property real ui: Math.max(1.0, Math.min(1.9, sysFont.height / 15.0))
    function px(n) { return Math.round(n * app.ui); }

    // --- brand ---------------------------------------------------------------
    readonly property color cBg: "#0a111c"
    readonly property color cSurface: "#111c2b"
    readonly property color cSurfaceHi: "#17243a"
    readonly property color cLine: "#22334d"
    readonly property color cText: "#e8eef7"
    readonly property color cDim: "#93a4bd"
    readonly property color cBrand: "#3fa9f5"
    readonly property color cBarBg: "#132338"

    // --- contrast, computed rather than guessed ------------------------------
    // WCAG 2.x relative luminance, straight from the spec. The text colours in
    // this window all passed when they were measured; the BORDERS did not.
    // cLine on cSurface is 1.35:1, and on a card whose only outline is that
    // border, SC 1.4.11 asks for 3:1 — the card edge is what tells you a card
    // is there at all. Deriving it keeps the same hue and stops the number
    // being a matter of opinion.
    function lumOf(c) {
        function lin(v) {
            return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        }
        return 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
    }

    function ratioOf(a, b) {
        var la = app.lumOf(a);
        var lb = app.lumOf(b);
        return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
    }

    // The two inks MUST be color objects, not string literals — the identical
    // bug firstrun/main.qml documents and fixed, which never reached this file.
    // lumOf reads c.r/c.g/c.b; a JavaScript string has none, so each came back
    // undefined, the arithmetic produced NaN, and `NaN >= NaN` below is false —
    // so onColor returned the dark ink on every accent, forever. It read like a
    // computation and behaved like a constant, and the shipped styles hid it:
    // six of seven carry a thumbnail so the fallback tile never draws, and the
    // seventh (highcontrast) has a light accent that wants dark ink anyway. A
    // drop-in style with a DARK accent and no thumbnail — a documented,
    // supported case — would have drawn a near-black initial letter on a
    // near-black tile.
    readonly property color inkLight: "#ffffff"
    readonly property color inkDark:  "#0a111c"

    function onColor(bg) {
        // bg arrives as a color object from cBrand, but as a plain STRING from
        // the model (entry.accent). lumOf needs .r/.g/.b, which a string does
        // not have, so coerce it — otherwise the string-accent call site is
        // NaN for the same reason the literals were.
        var b = (typeof bg === "string") ? Qt.color(bg) : bg;
        return app.ratioOf(app.inkLight, b) >= app.ratioOf(app.inkDark, b)
               ? app.inkLight : app.inkDark;
    }

    function readable(fg, bg, need) {
        var c = fg;
        var up = app.lumOf(bg) < 0.18;
        for (var i = 0; i < 24 && app.ratioOf(c, bg) < need; i++)
            c = up ? Qt.lighter(c, 1.10) : Qt.darker(c, 1.10);
        return c;
    }

    // Cards sit on cSurface; the tab strip and the empty-state sit on cBg.
    // Chained so the one colour clears 3:1 on both.
    readonly property color cEdge: app.readable(app.readable(app.cLine, app.cSurface, 3.0),
                                                app.cBg, 3.0)
    readonly property color cOnBrand: app.onColor(app.cBrand)

    // --- catalogue -----------------------------------------------------------
    property string edition: "free"
    property var styles: []
    property var layouts: []
    property string loadError: ""
    property bool loaded: false

    function send(msg) {
        console.log("@DAGRIC@" + msg);
    }

    // One sentence, ending in exactly one full stop, ready to have another
    // sentence appended to it. Catalogue text is written by whoever added the
    // theme and is inconsistent about its final punctuation.
    function sentence(s) {
        var t = ("" + (s ? s : "")).replace(/\s+$/, "");
        if (t === "")
            return "";
        return /[.!?]$/.test(t) ? t : t + ".";
    }

    // Speak without moving focus. announce() landed in Qt 6.8 and Debian
    // trixie ships 6.8.2, but a window that throws on an older runtime is
    // worse than one that stays quiet, so it is guarded.
    function say(msg, urgent) {
        try {
            if (typeof body.Accessible.announce === "function")
                body.Accessible.announce(msg, urgent ? Accessible.Assertive
                                                     : Accessible.Polite);
        } catch (e) {
            // No announcement channel here. Silence is the correct fallback.
        }
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
            if (!app.loaded && app.loadError === "") {
                app.loadError = "The appearance catalogue could not be read.";
                app.say(app.loadError, true);
            }
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
            app.say("Still previewing " + entry.name + ". "
                    + app.previewSeconds + " seconds again.", false);
            return;
        }
        app.previewKind = entry.kind;
        app.previewId = entry.id;
        app.previewName = entry.name;
        app.previewing = true;
        app.secondsLeft = app.previewSeconds;
        app.send("PREVIEW|" + entry.kind + "|" + entry.id);
        countdown.restart();
        // Assertive, and only here. Something just changed the whole desktop
        // and there is a clock running on it: that outranks whatever Orca was
        // part-way through saying. Focus is left exactly where it was.
        app.say("Previewing " + entry.name + ". Reverting in "
                + app.previewSeconds + " seconds. Press Keep to keep it, "
                + "More time for longer, or Escape to put it back.", true);
    }

    function moreTime() {
        if (!app.previewing)
            return;
        app.secondsLeft = app.secondsLeft + app.previewSeconds;
        countdown.restart();
        app.say(app.secondsLeft + " seconds.", false);
    }

    function keep() {
        if (!app.previewing)
            return;
        countdown.stop();
        app.send("KEEP|" + app.previewKind + "|" + app.previewId);
        app.say(app.previewName + " kept.", false);
        app.previewing = false;
        app.previewKind = "";
        app.previewId = "";
    }

    function revert() {
        if (!app.previewing)
            return;
        countdown.stop();
        app.send("REVERT|" + app.previewKind + "|" + app.previewId);
        app.say(app.previewName + " put back.", false);
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
            // Warn before it expires rather than after. Ten seconds is enough
            // to reach for More time; five is the last honest chance. Speaking
            // every second would make the window unusable with a screen reader
            // and tell nobody anything they did not already know.
            if (app.secondsLeft === 10 || app.secondsLeft === 5)
                app.say(app.secondsLeft + " seconds left. Keep, or More time.", false);
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

    // =========================================================== small pieces

    // A focus indicator that cannot be lost against its background.
    //
    // One ring in one colour would be enough on the flat surfaces here, but the
    // cards are covered by thumbnails of the very themes on offer — some of
    // them light, some dark, some the brand blue — and a single stroke will
    // always disappear against one of them. Two strokes, light outside dark,
    // means whatever is underneath cannot hide both. Measured on a rendered
    // screenshot rather than judged by eye: 19:1 between the strokes, and at
    // worst 18.9:1 against the window background.
    component FocusRing: Item {
        id: fr
        property real ringRadius: 12
        property bool on: false
        anchors.fill: parent
        visible: fr.on
        z: 40

        Rectangle {
            anchors.fill: parent
            anchors.margins: -app.px(4)
            radius: fr.ringRadius + app.px(4)
            color: "transparent"
            border.width: app.px(2)
            border.color: "#ffffff"
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -app.px(2)
            radius: fr.ringRadius + app.px(2)
            color: "transparent"
            border.width: app.px(2)
            border.color: "#0a0f16"
        }
    }

    // --- one card in the grid ------------------------------------------------
    Component {
        id: cardDelegate

        Item {
            id: cell
            required property var modelData
            required property int index
            width: GridView.view ? GridView.view.cellWidth : app.px(240)
            height: GridView.view ? GridView.view.cellHeight : app.px(200)

            property var entry: cell.modelData
            readonly property bool showing: app.isShowing(cell.entry)

            // Roving focus. The grid owns the single tab stop and the arrow
            // keys move between cards, which is how every picture grid on the
            // desktop behaves — and it keeps a gallery of twenty themes from
            // becoming twenty things to Tab past. Because the CURRENT card
            // holds real focus, Orca announces the theme you just arrowed onto
            // instead of saying "list" once and then nothing.
            focus: cell.GridView.isCurrentItem

            Accessible.role: Accessible.Button
            Accessible.name: cell.entry.name
                             + (cell.entry.pro === true ? ", Pro edition" : "")
            // The catalogue's descriptions already end in a full stop, so
            // joining them naively produced "…blue highlights.. Press to try".
            // A screen reader reads that as a stumble, which is exactly the
            // sort of thing that makes a product sound unfinished.
            Accessible.description: app.sentence(cell.entry.desc)
                                    + " Press to try it on for "
                                    + app.previewSeconds + " seconds."
            Accessible.focusable: true
            Accessible.focused: cell.activeFocus
            Accessible.selected: cell.showing
            Accessible.onPressAction: app.preview(cell.entry)

            // Arrow keys are deliberately left unaccepted so they bubble up to
            // the GridView, which is what moves the current index.
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                        || event.key === Qt.Key_Enter) {
                    app.preview(cell.entry);
                    event.accepted = true;
                }
            }

            Rectangle {
                id: card
                anchors.fill: parent
                anchors.margins: app.px(8)
                radius: app.px(12)
                color: mouse.containsMouse ? app.cSurfaceHi : app.cSurface
                border.width: cell.showing ? 2 : 1
                border.color: cell.showing ? app.cBrand : app.cEdge

                Behavior on color {
                    ColorAnimation { duration: 120 }
                }

                FocusRing { ringRadius: app.px(12); on: cell.activeFocus }

                ColumnLayout {
                    id: cardCol
                    anchors.fill: parent
                    anchors.margins: app.px(10)
                    spacing: app.px(8)

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
                            radius: app.px(6)
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: cell.entry.accent }
                                GradientStop { position: 1.0; color: app.cBg }
                            }
                            Text {
                                anchors.centerIn: parent
                                text: (cell.entry.name && cell.entry.name.length > 0)
                                      ? cell.entry.name.charAt(0).toUpperCase() : "?"
                                // Was a flat white that could land on a pale
                                // accent. The initial is decoration, but an
                                // illegible one still looks like a rendering
                                // bug to the person who can see it.
                                color: app.onColor(cell.entry.accent)
                                opacity: 0.9
                                font.bold: true
                                font.pixelSize: Math.max(app.px(22),
                                                         Math.round(parent.height * 0.42))
                                // The card already carries the name; a lone
                                // capital letter in the tree helps nobody.
                                Accessible.ignored: true
                            }
                        }

                        Image {
                            id: thumb
                            anchors.fill: parent
                            source: cell.entry.thumb ? cell.entry.thumb : ""
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            visible: status === Image.Ready
                            Accessible.ignored: true
                        }

                        Rectangle {
                            visible: cell.entry.pro === true
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: app.px(6)
                            width: proTag.implicitWidth + app.px(12)
                            height: proTag.implicitHeight + app.px(6)
                            radius: app.px(4)
                            color: app.cBg
                            opacity: 0.88
                            Text {
                                id: proTag
                                anchors.centerIn: parent
                                text: "PRO"
                                color: app.cBrand
                                font.pixelSize: app.px(10)
                                font.bold: true
                                // Folded into the card's own name instead, so
                                // it is heard as "Ember, Pro edition" and not
                                // as a stray "PRO" floating beside it.
                                Accessible.ignored: true
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: cell.entry.name
                        color: app.cText
                        font.pixelSize: app.px(14)
                        font.bold: true
                        elide: Text.ElideRight
                        Accessible.ignored: true
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        text: cell.entry.desc
                        color: app.cDim
                        font.pixelSize: app.px(12)
                        wrapMode: Text.WordWrap
                        elide: Text.ElideRight
                        maximumLineCount: 2
                        verticalAlignment: Text.AlignTop
                        Accessible.ignored: true
                    }
                }

                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        // Move the grid's current item to what was clicked, so
                        // the arrow keys carry on from where the mouse left
                        // off rather than jumping back to the top.
                        if (cell.GridView.view) {
                            cell.GridView.view.currentIndex = cell.index;
                            cell.GridView.view.forceActiveFocus(Qt.MouseFocusReason);
                        }
                        app.preview(cell.entry);
                    }
                }
            }
        }
    }

    // ============================================================ the window
    //
    // Header, body and footer are laid out here by hand rather than through
    // ApplicationWindow's header:/footer: properties, for the reason spelled
    // out in firstrun/main.qml: those properties put their items outside the
    // content item and Qt builds the Tab chain from tree order, so the focus
    // chain came out in the wrong order. Declaring the three in visual order
    // makes it correct by construction.
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

    // --- header --------------------------------------------------------------
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: app.px(76)
        color: app.cSurface

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: app.cLine
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: app.px(18)
            anchors.rightMargin: app.px(18)
            spacing: app.px(14)

            Rectangle {
                Layout.preferredWidth: app.px(40)
                Layout.preferredHeight: app.px(40)
                Layout.alignment: Qt.AlignVCenter
                radius: app.px(11)
                color: app.cBrand
                Accessible.ignored: true          // brand mark, not information
                Text {
                    anchors.centerIn: parent
                    text: "D"
                    color: app.cOnBrand
                    font.pixelSize: app.px(23)
                    font.bold: true
                    Accessible.ignored: true
                }
            }

            // minimumWidth 0 throughout: without it this block refuses to
            // shrink below the width of its own strapline and the Pro badge
            // gets pushed off the right-hand edge on a narrow window.
            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: "Dagric Appearance"
                    color: app.cText
                    font.pixelSize: app.px(18)
                    font.bold: true
                    elide: Text.ElideRight
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Dagric Appearance"
                }
                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    visible: app.width >= app.px(620)
                    text: "Click anything to try it on. Nothing is kept until you press Keep."
                    color: app.cDim
                    font.pixelSize: app.px(12)
                    elide: Text.ElideRight
                    Accessible.role: Accessible.StaticText
                    // elide chops the VISIBLE text; the spoken text is the
                    // whole sentence, not "Click anything to try it…"
                    Accessible.name: "Click anything to try it on. Nothing is kept until you press Keep."
                }
            }

            Rectangle {
                visible: app.edition === "pro"
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: proLabel.implicitWidth + app.px(18)
                Layout.preferredHeight: app.px(24)
                radius: app.px(12)
                color: "transparent"
                border.width: 1
                border.color: app.cBrand
                Text {
                    id: proLabel
                    anchors.centerIn: parent
                    text: "PRO EDITION"
                    color: app.cBrand
                    font.pixelSize: app.px(10)
                    font.bold: true
                    Accessible.role: Accessible.StaticText
                    Accessible.name: "Pro edition"
                }
            }
        }
    }

    // --- body ----------------------------------------------------------------
    ColumnLayout {
        id: body
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 0

        TabBar {
            id: tabs
            Layout.fillWidth: true
            background: Rectangle { color: app.cBg }
            // TabBar already gives its buttons a PageTab role, Left/Right
            // navigation and Space activation — it was the one thing in this
            // window that worked. What it did not have was anything to SEE:
            // overriding contentItem and background throws the style's focus
            // visual away, so a keyboard user could move between the tabs
            // without any idea which one they were on.
            Accessible.role: Accessible.PageTabList
            Accessible.name: "Gallery"


            // LEAVE THE BUTTONS ALONE. This is deliberate, and it cost a
            // while to establish, so it is written down rather than rediscovered.
            //
            // The obvious "improvement" here is to declare role, name and a
            // helpful description on each TabButton the way every other
            // control in these two files now does. Do not. On Qt 6.8.2,
            // annotating a TabButton makes it report Accessible.ignored ==
            // true a moment after the window is laid out — the annotation
            // DELETES the tab from the accessibility tree, which is the exact
            // opposite of the intent, and it is silent. Reading the attached
            // property back is the only way to see it; a bare TabBar reads
            // false on every button, an annotated one does not. Setting
            // ignored back to false imperatively does not survive either,
            // because whatever flips it runs later than Component.onCompleted
            // and later than Qt.callLater.
            //
            // TabBar and TabButton are first-class accessible controls: Qt
            // gives them the PageTab role, the name from `text`, Left/Right
            // navigation and Space activation on its own. Tabs were in fact
            // the ONLY part of this window that already worked. What they were
            // missing was something to LOOK at — overriding background and
            // contentItem throws away the style's focus visual, so a keyboard
            // user could move between tabs with no idea where they were. That
            // is what the FocusRing below fixes, and it is all that changed.
            TabButton {
                id: tabStyles
                text: "Styles"
                background: Rectangle {
                    color: "transparent"
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: tabStyles.checked ? 3 : 1
                        color: tabStyles.checked ? app.cBrand : app.cEdge
                    }
                    FocusRing { ringRadius: app.px(4); on: tabStyles.activeFocus }
                }
                contentItem: Text {
                    text: tabStyles.text
                    color: tabStyles.checked ? app.cText : app.cDim
                    font.pixelSize: app.px(14)
                    font.bold: tabStyles.checked
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Accessible.ignored: true
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
                        color: tabLayouts.checked ? app.cBrand : app.cEdge
                    }
                    FocusRing { ringRadius: app.px(4); on: tabLayouts.activeFocus }
                }
                contentItem: Text {
                    text: tabLayouts.text
                    color: tabLayouts.checked ? app.cText : app.cDim
                    font.pixelSize: app.px(14)
                    font.bold: tabLayouts.checked
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Accessible.ignored: true
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
                    anchors.margins: app.px(8)
                    clip: true
                    visible: app.styles.length > 0
                    model: app.styles
                    delegate: cardDelegate
                    cacheBuffer: 600

                    activeFocusOnTab: true
                    keyNavigationEnabled: true
                    keyNavigationWraps: false

                    Accessible.role: Accessible.List
                    Accessible.name: "Styles"
                    Accessible.description: "Arrow keys to move between styles, Space to try one on"

                    property int columns: Math.max(1, Math.floor(width / app.px(250)))
                    cellWidth: Math.floor(width / columns)
                    cellHeight: Math.round((cellWidth - app.px(36)) * 0.5625) + app.px(104)

                    ScrollBar.vertical: ScrollBar {
                        contentItem: Rectangle {
                            implicitWidth: app.px(6)
                            radius: app.px(3)
                            color: app.cEdge
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    width: parent.width - app.px(60)
                    visible: app.styles.length === 0
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: app.cDim
                    font.pixelSize: app.px(13)
                    text: app.loadError !== ""
                          ? app.loadError
                          : "No styles are installed. Reinstall the dagric-branding package to restore them."
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }

            Item {
                GridView {
                    id: layoutGrid
                    anchors.fill: parent
                    anchors.margins: app.px(8)
                    clip: true
                    visible: app.layouts.length > 0
                    model: app.layouts
                    delegate: cardDelegate
                    cacheBuffer: 600

                    activeFocusOnTab: true
                    keyNavigationEnabled: true
                    keyNavigationWraps: false

                    Accessible.role: Accessible.List
                    Accessible.name: "Layouts"
                    Accessible.description: "Arrow keys to move between layouts, Space to try one on"

                    property int columns: Math.max(1, Math.floor(width / app.px(250)))
                    cellWidth: Math.floor(width / columns)
                    cellHeight: Math.round((cellWidth - app.px(36)) * 0.5625) + app.px(104)

                    ScrollBar.vertical: ScrollBar {
                        contentItem: Rectangle {
                            implicitWidth: app.px(6)
                            radius: app.px(3)
                            color: app.cEdge
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    width: parent.width - app.px(60)
                    visible: app.layouts.length === 0
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: app.cDim
                    font.pixelSize: app.px(13)
                    text: app.loadError !== ""
                          ? app.loadError
                          : "No layouts are installed. Reinstall the dagric-branding package to restore them."
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }
        }
    }

    // --- the preview bar -----------------------------------------------------
    // The whole point of this application. It stays on screen for as long as
    // something is on trial, and it never lies about what happens next.
    Rectangle {
        id: bar
        Layout.fillWidth: true
        // Content-driven, not a fixed 72. At 150% text three buttons and a
        // sentence no longer fit on one line, and a fixed height meant the
        // row simply ran off the right-hand edge — taking Keep with it, which
        // is the one control that makes a preview permanent. It wraps now, and
        // the bar grows to match.
        Layout.preferredHeight: app.previewing ? barFlow.implicitHeight + app.px(22) : 0
        visible: app.previewing
        color: app.cBarBg

        // Named as a group so a screen reader arriving here is told what this
        // strip is before it starts reading buttons out of it.
        Accessible.role: Accessible.Grouping
        Accessible.name: app.previewing
                         ? ("Previewing " + app.previewName + ", "
                            + app.secondsLeft + " seconds left") : ""

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 2
            color: app.cBrand
        }

        // A Flow, not a RowLayout. A Layout squeezes or overflows; a Flow puts
        // what will not fit on the next line, which is the only honest answer
        // when the buttons alone are wider than the window. The message block
        // takes whatever is left over once the buttons have their space, down
        // to a floor, and below that the buttons wrap under it.
        Flow {
            id: barFlow
            x: app.px(18)
            y: app.px(12)
            width: Math.max(app.px(80), bar.width - app.px(36))
            spacing: app.px(12)
            visible: app.previewing

            Column {
                id: barInfo
                width: {
                    var buttons = moreBtn.width + revertBtn.width + keepBtn.width
                                  + barFlow.spacing * 3;
                    return Math.max(app.px(150), barFlow.width - buttons);
                }
                spacing: app.px(3)

                Text {
                    width: barInfo.width
                    text: "Previewing " + app.previewName
                    color: app.cText
                    font.pixelSize: app.px(15)
                    font.bold: true
                    elide: Text.ElideRight
                    // The group above says this; repeating it here would have
                    // Orca read the same sentence twice on the way in.
                    Accessible.ignored: true
                }

                Row {
                    spacing: app.px(10)
                    Text {
                        text: app.secondsLeft === 1
                              ? "Reverting in 1 second"
                              : "Reverting in " + app.secondsLeft + " seconds"
                        color: app.cDim
                        font.pixelSize: app.px(12)
                        // A number that changes every second must not be a
                        // live announcement: Orca would talk over itself for
                        // twenty seconds straight. The countdown is spoken at
                        // ten and five seconds by the timer instead.
                        Accessible.ignored: true
                    }
                    Rectangle {
                        width: app.px(110)
                        height: app.px(5)
                        anchors.verticalCenter: parent.verticalCenter
                        radius: app.px(3)
                        color: app.cEdge
                        Accessible.ignored: true      // a picture of the number
                        Rectangle {
                            height: parent.height
                            radius: app.px(3)
                            color: app.cBrand
                            width: parent.width * Math.max(0, Math.min(1, app.secondsLeft / app.previewSeconds))
                            Behavior on width {
                                NumberAnimation { duration: 280 }
                            }
                        }
                    }
                }
            }

            // WCAG 2.2.1 Timing Adjustable, Level A. Twenty seconds is ample
            // if you can see the bar and reach for a mouse; it is not if a
            // screen reader has to read it to you first, and running out
            // silently throws away the choice you just made. Pressing this
            // adds twenty more, as often as you like.
            Button {
                id: moreBtn
                text: "More time"
                Accessible.role: Accessible.Button
                Accessible.name: moreBtn.text
                Accessible.focusable: true
                Accessible.focused: moreBtn.activeFocus
                Accessible.onPressAction: moreBtn.clicked()
                height: app.px(36)
                width: app.px(112)
                Accessible.description: "Add another " + app.previewSeconds
                                        + " seconds before this is put back"
                Keys.onReturnPressed: function(event) { moreBtn.clicked(); event.accepted = true; }
                Keys.onEnterPressed:  function(event) { moreBtn.clicked(); event.accepted = true; }
                onClicked: app.moreTime()
                background: Rectangle {
                    radius: app.px(8)
                    color: moreBtn.down ? "#1b2c44" : "transparent"
                    border.width: 1
                    border.color: app.cEdge
                    FocusRing { ringRadius: app.px(8); on: moreBtn.activeFocus }
                }
                contentItem: Text {
                    text: moreBtn.text
                    color: app.cText
                    font.pixelSize: app.px(13)
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Accessible.ignored: true
                }
            }

            Button {
                id: revertBtn
                text: "Revert"
                Accessible.role: Accessible.Button
                Accessible.name: revertBtn.text
                Accessible.focusable: true
                Accessible.focused: revertBtn.activeFocus
                Accessible.onPressAction: revertBtn.clicked()
                height: app.px(36)
                width: app.px(104)
                Accessible.description: "Put the desktop back the way it was, now"
                Keys.onReturnPressed: function(event) { revertBtn.clicked(); event.accepted = true; }
                Keys.onEnterPressed:  function(event) { revertBtn.clicked(); event.accepted = true; }
                onClicked: app.revert()
                background: Rectangle {
                    radius: app.px(8)
                    color: revertBtn.down ? "#1b2c44" : "transparent"
                    border.width: 1
                    border.color: app.cEdge
                    FocusRing { ringRadius: app.px(8); on: revertBtn.activeFocus }
                }
                contentItem: Text {
                    text: revertBtn.text
                    color: app.cText
                    font.pixelSize: app.px(13)
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Accessible.ignored: true
                }
            }

            Button {
                id: keepBtn
                text: "Keep"
                Accessible.role: Accessible.Button
                Accessible.name: keepBtn.text
                Accessible.focusable: true
                Accessible.focused: keepBtn.activeFocus
                Accessible.onPressAction: keepBtn.clicked()
                height: app.px(36)
                width: app.px(104)
                Accessible.description: "Stop the countdown and keep "
                                        + app.previewName + " for good"
                Keys.onReturnPressed: function(event) { keepBtn.clicked(); event.accepted = true; }
                Keys.onEnterPressed:  function(event) { keepBtn.clicked(); event.accepted = true; }
                onClicked: app.keep()
                background: Rectangle {
                    radius: app.px(8)
                    color: keepBtn.down ? "#2f8ed0" : app.cBrand
                    FocusRing { ringRadius: app.px(8); on: keepBtn.activeFocus }
                }
                contentItem: Text {
                    text: keepBtn.text
                    color: app.cOnBrand
                    font.pixelSize: app.px(13)
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Accessible.ignored: true
                }
            }
        }
    }

    }   // end of the header / body / preview-bar column
}
