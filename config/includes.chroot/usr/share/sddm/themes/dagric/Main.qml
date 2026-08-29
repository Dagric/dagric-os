// SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Dagric OS — the login screen.
//
// On an installed machine this is the screen the owner sees every single boot,
// more often than any other screen in the product. Until this file existed it
// was Breeze's layout with a Dagric background and logo pushed in through
// usr/share/sddm/themes/breeze/theme.conf.user. That worked, and it had two
// problems: Breeze's Main.qml only reads six keys, so there was nothing further
// to reach without a real theme; and the layout belonged to KDE, so a Plasma
// update could rearrange our login screen without us touching anything.
//
// ============================================ THE FAILURE THAT MATTERS MOST
//
// If this file does not load, the owner cannot get to their desktop, and there
// is no way round that from inside the product. So here is exactly what SDDM
// 0.21 does when a theme is broken, in the three ways it can be. This is not
// repeated from documentation: the messages are strings pulled out of the
// shipped /usr/bin/sddm and /usr/bin/sddm-greeter-qt6, and cases 1 and 3 were
// reproduced by breaking a copy of THIS file and running that same greeter
// binary against it under Xvfb.
//
//  1. THEME DIRECTORY MISSING. The daemon logs "The configured theme <name>
//     doesn't exist, using the embedded theme instead" and starts its built-in
//     greeter. Unbranded, and it logs you in.
//
//  2. metadata.desktop DOES NOT SAY QtVersion=6. The daemon resolves the
//     greeter binary from that key, looks for sddm-greeter-qt5, does not find
//     it (Debian 13 ships only the Qt 6 greeter), logs "The theme at <path>
//     requires missing <binary>. Using fallback theme." and again falls back.
//     This is the single most common cause of the "my SDDM theme is a black
//     screen" reports you will find online, which are nearly always a Qt 5
//     theme on Plasma 6.
//
//  3. MainScript IS PRESENT BUT THE QML DOES NOT COMPILE — a missing import, a
//     typo, a module somebody dropped from the package list. I expected this
//     one to be the lockout, because the greeter's file-missing fallback
//     obviously cannot fire when the file is there. It is not. Verified by
//     adding "import org.kde.kirigami 2.20" to a copy of this file: the
//     greeter prints the QML errors, logs "Fallback to embedded theme", and
//     the embedded theme comes up AND PRINTS THE ERROR ON SCREEN in red —
//     "The current theme cannot be loaded due to the errors below, please
//     select another theme", followed by the offending line — above a working
//     user list, password box, session picker and layout picker. Grim, but the
//     owner logs in and the reason is on the screen rather than in a journal
//     they cannot reach.
//
//     ONE CONDITION MAKES THAT UNTRUE, and it is worth knowing: the embedded
//     theme itself imports SddmComponents 2.0, which lives in
//     /usr/lib/x86_64-linux-gnu/qt6/qml/SddmComponents and is shipped by the
//     sddm package itself (checked against the built ISO). On a machine where
//     that is absent, the fallback fails to compile too, the greeter retries
//     it forever, and the screen is black — I saw precisely that on a test box
//     without it. So: never split SddmComponents out of the image.
//
// None of which makes a bad login screen acceptable. Falling back means the
// owner meets stock SDDM and a red error message on the machine they paid for.
// The defence is still to have nothing that can go missing: THIS FILE IMPORTS
// QtQuick AND NOTHING ELSE. No Kirigami, no org.kde.plasma.*, no
// org.kde.breeze.components, no Qt5Compat.GraphicalEffects, no
// QtQuick.Controls, no QtQuick.Layouts. Every one of those is a package that
// could be dropped from config/package-lists/desktop.list.chroot by somebody
// trimming the image, and two of them (org.kde.plasma.private.keyboardindicator
// and org.kde.breeze.components, both of which Breeze's own theme needs) are
// private KDE modules with no compatibility promise at all.
// qml6-module-qtquick cannot be dropped: Plasma will not start without it, so
// a build that loses it has no desktop to log in to anyway.
//
// Consequences of that rule, so nobody "fixes" them later:
//   - buttons are Rectangle + MouseArea + Keys, not QtQuick.Controls Buttons;
//   - layout is anchors and Column, not QtQuick.Layouts;
//   - the round avatar is masked by Canvas, because a circular mask otherwise
//     needs QtQuick.Effects or Qt5Compat (clip: is rectangular and will not do
//     it) — see the note on the avatar below;
//   - the caps-lock indicator uses SDDM's own keyboard model, not Plasma's
//     KeyState, which is the private import Breeze depends on.
//
// ============================================================ ACCESSIBILITY
//
// Read /etc/sddm.conf.d/20-accessibility.conf before changing anything here.
// The short version of that analysis: a screen reader at the SDDM greeter is
// not achievable — SDDM cannot publish an AT-SPI bus its own Qt greeter would
// join — and nothing in this file changes that. The Accessible.role and
// Accessible.name declarations below are here because they are free, correct,
// and would start working the day SDDM gains that support. They are not a
// claim that Orca can read this screen today. It cannot.
//
// What IS achievable, and is done here:
//   - every control is reachable by Tab, in reading order, and answers Space
//     and Enter as well as the mouse;
//   - focus is always visible, drawn as two rings (light outside, dark inside)
//     so it survives whatever the backdrop is doing underneath — the same
//     device the first-run wizard uses, for the same reason;
//   - text is deliberately larger than a desktop's. The password field is
//     20px at 1080p, the name 30px, the clock 76px;
//   - contrast is measured, not eyeballed. Against the shipped backdrop
//     (usr/share/dagric/sddm/background.png, built by branding/sddm/
//     make-login-art.sh) the ink measures 18:1 in the centre and 14.8:1 over
//     the brightest part of the contour band at the bottom. The dimmest colour
//     used, cMuted, measures 6.7:1 there. WCAG AA wants 4.5:1.
//
// ================================================================ THE LOOK
//
// Palette, type and spacing come from usr/share/dagric/firstrun/main.qml and
// usr/share/dagric/manual/manual.css so the chain — boot splash, login, first
// run, manual — reads as one product rather than four. #3fa9f5 is the brand
// blue, #f0a658 the warning amber, 12px the corner radius, and the navy is the
// same #0a111c the wizard and the manual use.
//
// The shape is Windows', on purpose. Everyone buying this is leaving Windows
// 10, and the login screen is not the place to teach them something new: a big
// clock and a long date above, one avatar, one name, one password box with the
// arrow on its right, and the power controls in the bottom corner. Session and
// keyboard-layout pickers are present but small, quiet and bottom-left, and
// they hide entirely when there is only one thing to pick — a chooser with one
// entry teaches the owner that their choices do not matter.
//
// ============================================================= TRANSLATION
//
// Every visible string below is inside qsTr(). Until that was true this screen
// was English in all six languages — the one screen an owner cannot avoid, seen
// on every boot, and a REGRESSION, because the Breeze theme this one replaced
// is translated upstream into all six.
//
// qsTr(), not the gettext road every other Dagric string travels. The wizard's
// long note in usr/bin/dagric-firstrun rejects qsTr for good reasons; none of
// them hold here. That note's argument rests on the wizard being launched by
// our own shell script, which can look strings up in the gettext catalogue and
// hand them to the QML as data. NOTHING OF OURS LAUNCHES THIS FILE. SDDM reads
// metadata.desktop and loads it into its own engine, as the `sddm` user, before
// any Dagric code runs. There is no seam to pass strings through, so the only
// mechanism available is the one SDDM implements — and it does implement one.
//
// It is also not a second translation system in the sense that note meant: it
// adds no runtime dependency and nothing to the image but five small files.
// qsTr() is a QML built-in and needs NO import, so the rule at the top of this
// file — QtQuick and nothing else — still holds exactly as written.
//
// The catalogues are translations/<locale>.qm, and metadata.desktop's
// TranslationsDirectory key is what points SDDM at them; the full read of the
// SDDM source, and the Qt 6.8 experiment that confirmed which filename each
// locale resolves to, are written out there rather than repeated here.
//
// Two things that are deliberately NOT translated, so nobody adds them later:
//   - the clock and the date (they already follow the locale, because they go
//     through Qt.locale() and Locale.LongFormat rather than a format string);
//   - the edition badge, the user's name, session names and keyboard layout
//     names. Those are data — from theme.conf, from the user database and from
//     SDDM's own models — not sentences of ours, and translating a value that
//     came out of a database is how you get a session called "Bureau".
//
// If you add a string, wrap it in qsTr() and then, from this directory:
//
//     lupdate Main.qml -ts translations/de.ts translations/es.ts \
//                          translations/fr.ts translations/it.ts \
//                          translations/pt_BR.ts
//     # fill in the new <translation> elements, then:
//     lrelease translations/*.ts
//
// On Debian those two live in /usr/lib/qt6/bin and come from qt6-l10n-tools,
// which is a BUILD-HOST package: nothing in the image depends on it, because
// only the compiled .qm ships. Leaving a <translation type="unfinished"> in a
// .ts is not an error and not a build failure — lrelease drops the message and
// that one string silently reverts to English. Check the counts lrelease prints
// against the number of qsTr() calls in this file.

import QtQuick

Item {
    id: root

    // SDDM resizes the root object to its view, exactly as Breeze does; these
    // are only the size the file gets when it is opened in a plain QML runner.
    width: 1600
    height: 900

    // ---------------------------------------------------------------- scale
    // One number drives every dimension. At 1080p and below it is 1.0, which
    // is the size everything below was designed at; above that it grows, so a
    // 4K panel does not get a login form the size of a postage stamp. Clamped
    // at both ends: never smaller than the design (a 1024x768 machine gets the
    // full-size form and simply has less room around it), and never past 1.7,
    // because beyond that the form starts to run off the bottom of a short
    // screen. The clamp at the low end is why every vertical measurement below
    // has to fit inside 768 pixels — it does, with 170 to spare.
    readonly property real ui: Math.max(1.0, Math.min(1.7, root.height / 1080))
    function px(n) { return Math.round(n * root.ui); }

    // Below this the clock is dropped and the form moves up. 640 is chosen so
    // an ordinary 1024x768 or 800x600 VM window keeps everything; only genuinely
    // tiny viewports lose the clock, and they lose the decoration, not a control.
    readonly property bool compact: root.height < root.px(640)

    // ------------------------------------------------------------- palette
    readonly property color cInk:    "#f2f7fd"
    readonly property color cSoft:   "#c9d6e6"
    readonly property color cMuted:  "#9fb0c6"
    readonly property color cAccent: "#3fa9f5"
    readonly property color cWarm:   "#f0a658"
    readonly property color cField:  Qt.rgba(0.024, 0.043, 0.078, 0.66)
    readonly property color cEdge:   Qt.rgba(0.58, 0.70, 0.84, 0.38)
    readonly property color cEdgeHi: Qt.rgba(0.75, 0.85, 0.96, 0.62)

    // ---------------------------------------------------------------- state
    property int  userIndex: 0
    property int  sessionIndex: 0
    property bool busy: false
    property string message: ""
    property bool messageIsWarning: false
    property bool showPassword: false
    property bool faceReady: false
    property date now: new Date()

    // The user the form is currently pointed at. `users` below is a Repeater
    // rather than a ListView on purpose: a Repeater builds every delegate
    // immediately and keeps them, so this is readable before anything is drawn
    // and stays readable while the switcher is closed. A ListView would only
    // have instantiated the rows it could see.
    readonly property var currentUser: (users.count > 0 && root.userIndex >= 0
                                        && root.userIndex < users.count)
                                       ? users.itemAt(root.userIndex) : null
    readonly property string userName:  root.anonymous ? root.typedName
                                                       : (root.currentUser ? root.currentUser.name : "")
    readonly property string userLabel: root.currentUser
                                        ? (root.currentUser.realName !== ""
                                           ? root.currentUser.realName : root.currentUser.name)
                                        : ""
    readonly property bool userNeedsPassword: root.currentUser ? root.currentUser.needsPassword : true
    readonly property var  userIcon: root.currentUser ? root.currentUser.icon : ""
    readonly property string userInitial: root.userLabel.length > 0
                                          ? root.userLabel.charAt(0).toUpperCase() : "?"

    // The user list can legitimately come back EMPTY: SDDM only lists accounts
    // between MinimumUid and MaximumUid and not named in [Users] HideUsers, and
    // an administrator can trim that to nothing. With a list-only login screen
    // that is a locked machine with no way in — the exact failure this theme is
    // supposed to be armoured against. So when there is nobody to point at, the
    // form grows a user-name box and behaves like the console login it has
    // become. Verified in the greeter's own test mode, which supplies no users
    // at all and is therefore this path.
    readonly property bool anonymous: users.count === 0
    readonly property string typedName: nameField.text

    // The C locale — which a machine with no locale configured genuinely has —
    // returns "HH:mm:ss" as its short time, and a seconds counter ticking away
    // on a login screen reads as a debug build. Neither Windows nor macOS shows
    // seconds here. Rather than hard-code "HH:mm" and take 12-hour clocks away
    // from everybody who uses one, take the locale's own short format and
    // delete the seconds field out of it. Every real locale already omits
    // seconds, so this only ever fires on the unconfigured machine.
    readonly property string timeFormat:
        Qt.locale().timeFormat(Locale.ShortFormat).replace(/[.:]?\s?s+/g, "")

    // Only offer a picker when there is something to pick. See the header note.
    readonly property bool haveUserChoice:   users.count > 1
    readonly property bool haveSessionChoice: sessions.count > 1
    readonly property bool haveLayoutChoice: keyboard.layouts.length > 1

    // -------------------------------------------------------------- actions
    function signIn() {
        if (root.busy || root.userName === "")
            return;
        root.message = "";
        root.busy = true;
        sddm.login(root.userName, pw.text, root.sessionIndex);
    }

    function pickUser(i) {
        root.userIndex = i;
        pw.text = "";
        root.message = "";
        root.showPassword = false;
        userSheet.visible = false;
        pw.forceActiveFocus();
    }

    function closeSheets() {
        userSheet.visible = false;
        sessionSheet.visible = false;
        layoutSheet.visible = false;
    }

    // SDDM talks back over these three signals and nothing else. Note that a
    // wrong password arrives as loginFailed with no text of its own, so the
    // wording is ours; informationMessage is PAM's own text (an expired
    // password, an account lock) and is shown verbatim, because paraphrasing
    // it would be guessing at what the module meant.
    Connections {
        target: sddm

        function onLoginFailed() {
            root.busy = false;
            root.messageIsWarning = true;
            root.message = root.userNeedsPassword
                           ? qsTr("That password wasn't right. Try again.")
                           : qsTr("Sign-in was refused.");
            pw.selectAll();
            pw.forceActiveFocus();
        }

        function onLoginSucceeded() {
            root.busy = false;
            root.message = "";
        }

        function onInformationMessage(message) {
            root.messageIsWarning = true;
            root.message = message;
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    Component.onCompleted: {
        if (userModel.lastIndex >= 0 && userModel.lastIndex < users.count)
            root.userIndex = userModel.lastIndex;
        if (sessionModel.lastIndex >= 0)
            root.sessionIndex = sessionModel.lastIndex;
        // Land on the first thing the owner has to fill in. With a user list
        // that is the password; without one it is the name, and focusing the
        // password box there would mean typing into a field that cannot submit.
        if (root.anonymous)
            nameField.forceActiveFocus();
        else
            pw.forceActiveFocus();
    }

    // Escape closes whatever is open. Declared once at the top rather than on
    // each sheet, so a sheet added later cannot forget to be closable.
    Shortcut {
        sequence: "Esc"
        onActivated: root.closeSheets()
    }

    // ======================================================= small pieces ==

    // A focus indicator that cannot be lost against its background.
    //
    // One ring in one colour is the usual answer and it is not safe here: the
    // backdrop is an image, and config.background can be pointed at a different
    // one. A light ring vanishes on pale pixels, a dark one on dark pixels. Two
    // rings, one just outside the other, cannot both vanish — whatever is
    // underneath is not simultaneously close to white and close to black. Same
    // component, same reasoning, as the first-run wizard.
    component FocusRing: Item {
        id: fr
        property real ringRadius: root.px(12)
        property bool on: false
        anchors.fill: parent
        visible: fr.on
        z: 40

        Rectangle {
            anchors.fill: parent
            anchors.margins: -root.px(4)
            radius: fr.ringRadius + root.px(4)
            color: "transparent"
            border.width: root.px(2)
            border.color: "#ffffff"
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -root.px(2)
            radius: fr.ringRadius + root.px(2)
            color: "transparent"
            border.width: root.px(2)
            border.color: "#06101c"
        }
    }

    // The one button shape in the theme. Bordered for the power controls,
    // borderless for the quiet pickers, same keyboard behaviour either way:
    // Space and Enter both activate, because a Windows switcher presses Enter
    // and a Qt Quick Controls Button would only have taken Space.
    component TextButton: Rectangle {
        id: tb
        property string label: ""
        property string hint: ""
        property bool quiet: false
        property color ink: root.cInk
        signal activated()

        implicitWidth: tbText.implicitWidth + root.px(tb.quiet ? 20 : 34)
        implicitHeight: root.px(tb.quiet ? 34 : 42)
        radius: root.px(10)
        color: tbArea.containsMouse ? Qt.rgba(1, 1, 1, tb.quiet ? 0.10 : 0.14)
                                    : (tb.quiet ? "transparent" : Qt.rgba(0, 0, 0, 0.28))
        border.width: tb.quiet ? 0 : 1
        border.color: tbArea.containsMouse ? root.cEdgeHi : root.cEdge
        activeFocusOnTab: true

        Accessible.role: Accessible.Button
        Accessible.name: tb.label
        Accessible.description: tb.hint
        Accessible.focusable: true
        Accessible.focused: tb.activeFocus
        Accessible.onPressAction: tb.activated()

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                    || event.key === Qt.Key_Enter) {
                tb.activated();
                event.accepted = true;
            }
        }

        FocusRing { ringRadius: tb.radius; on: tb.activeFocus }

        Text {
            id: tbText
            anchors.centerIn: parent
            text: tb.label
            color: tb.ink
            font.pixelSize: root.px(tb.quiet ? 14 : 16)
            Accessible.ignored: true
        }

        MouseArea {
            id: tbArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                tb.forceActiveFocus(Qt.MouseFocusReason);
                tb.activated();
            }
        }
    }

    // The arrow on the sign-in button, drawn from three rectangles rather than
    // set as the character "→". A glyph would be one missing font away from
    // rendering as an empty box on the most important control on the screen,
    // and the greeter runs as the sddm user with whatever fontconfig gives it.
    // Geometry: the tip sits at (width, height/2) and each barb is a bar of
    // length L rotated ±45° about its own centre, placed so one end lands on
    // the tip.
    component ArrowGlyph: Item {
        id: ag
        property color ink: root.cInk
        readonly property real bar: Math.max(2, root.px(2))
        readonly property real barb: ag.width * 0.42
        readonly property real off: ag.barb / 2 / Math.SQRT2

        Rectangle {
            x: 0
            y: ag.height / 2 - ag.bar / 2
            width: ag.width
            height: ag.bar
            radius: ag.bar / 2
            color: ag.ink
        }
        Rectangle {
            x: ag.width - ag.off - ag.barb / 2
            y: ag.height / 2 - ag.off - ag.bar / 2
            width: ag.barb
            height: ag.bar
            radius: ag.bar / 2
            color: ag.ink
            rotation: 45
        }
        Rectangle {
            x: ag.width - ag.off - ag.barb / 2
            y: ag.height / 2 + ag.off - ag.bar / 2
            width: ag.barb
            height: ag.bar
            radius: ag.bar / 2
            color: ag.ink
            rotation: -45
        }
    }

    // A modal list. Used for switching user, session and keyboard layout: three
    // things that are one-of-a-set choices and all belong in the same shape, so
    // the owner learns it once. Clicking outside or pressing Escape closes it.
    component Sheet: Item {
        id: sh
        property string title: ""
        default property alias content: shCol.data
        anchors.fill: parent
        visible: false
        z: 100

        MouseArea {
            anchors.fill: parent
            onClicked: sh.visible = false
        }

        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(0.016, 0.027, 0.051, 0.72)
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(root.px(460), root.width - root.px(60))
            height: Math.min(shCol.implicitHeight + root.px(52), root.height - root.px(80))
            radius: root.px(14)
            color: "#101b2c"
            border.width: 1
            border.color: Qt.rgba(0.58, 0.70, 0.84, 0.22)

            // Swallow clicks so they do not reach the dismiss area behind.
            MouseArea { anchors.fill: parent }

            Text {
                id: shTitle
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: root.px(18)
                text: sh.title
                color: root.cMuted
                font.pixelSize: root.px(14)
                Accessible.role: Accessible.Heading
                Accessible.name: sh.title
            }

            Column {
                id: shCol
                anchors.top: shTitle.bottom
                anchors.topMargin: root.px(10)
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: root.px(10)
                anchors.rightMargin: root.px(10)
                anchors.bottomMargin: root.px(14)
            }
        }
    }

    // One row inside a Sheet.
    component SheetRow: Rectangle {
        id: sr
        property string label: ""
        property string sub: ""
        property bool current: false
        signal activated()

        width: parent ? parent.width : 0
        height: root.px(52)
        radius: root.px(9)
        color: srArea.containsMouse ? Qt.rgba(1, 1, 1, 0.09)
                                    : (sr.current ? Qt.rgba(0.25, 0.66, 0.96, 0.16) : "transparent")
        activeFocusOnTab: true

        Accessible.role: Accessible.RadioButton
        Accessible.name: sr.label
        Accessible.description: sr.sub
        Accessible.focusable: true
        Accessible.focused: sr.activeFocus
        Accessible.checkable: true
        Accessible.checked: sr.current
        Accessible.onPressAction: sr.activated()
        Accessible.onToggleAction: sr.activated()

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                    || event.key === Qt.Key_Enter) {
                sr.activated();
                event.accepted = true;
            }
        }

        FocusRing { ringRadius: sr.radius; on: sr.activeFocus }

        Rectangle {
            id: srDot
            anchors.left: parent.left
            anchors.leftMargin: root.px(14)
            anchors.verticalCenter: parent.verticalCenter
            width: root.px(10)
            height: root.px(10)
            radius: width / 2
            color: sr.current ? root.cAccent : "transparent"
            border.width: sr.current ? 0 : 1
            border.color: root.cEdge
        }

        Text {
            anchors.left: srDot.right
            anchors.leftMargin: root.px(14)
            anchors.right: parent.right
            anchors.rightMargin: root.px(12)
            anchors.verticalCenter: parent.verticalCenter
            text: sr.sub !== "" ? sr.label + "   " + sr.sub : sr.label
            color: sr.current ? root.cInk : root.cSoft
            font.pixelSize: root.px(16)
            elide: Text.ElideRight
            Accessible.ignored: true
        }

        MouseArea {
            id: srArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                sr.forceActiveFocus(Qt.MouseFocusReason);
                sr.activated();
            }
        }
    }

    // ============================================================ models ==
    //
    // Both of these are Repeaters over SDDM's own models, kept off-screen, so
    // the rest of the file can read a user or a session as a plain object. The
    // property names are SDDM's role names and cannot be renamed: `name`,
    // `realName`, `icon` and `needsPassword` on the user model, `name` on the
    // session model. They were read out of the shipped greeter binary rather
    // than out of a tutorial.
    Item {
        visible: false

        Repeater {
            id: users
            model: userModel
            delegate: Item {
                required property string name
                required property string realName
                required property var icon
                required property bool needsPassword
            }
        }

        Repeater {
            id: sessions
            model: sessionModel
            delegate: Item {
                required property string name
            }
        }
    }

    // ======================================================== the backdrop ==

    // Drawn before the image and never removed. If background.png is missing,
    // unreadable by the sddm user, or config.type is not "image", this is what
    // the owner gets: the brand navy, and a login form that still works. A
    // login screen that depends on a PNG is a login screen that a bad file
    // permission can turn into a black rectangle.
    Rectangle {
        anchors.fill: parent
        color: config.color !== "" ? config.color : "#0a111c"
    }

    Image {
        anchors.fill: parent
        visible: config.type === "image" && status === Image.Ready
        source: config.type === "image" ? config.background : ""
        fillMode: Image.PreserveAspectCrop
        // Synchronous on purpose. This is the first frame after Plymouth hands
        // over; loading the backdrop in the background would show a flat navy
        // screen first and then snap to the real one, which is exactly the
        // extra transition the rest of the boot chain works to remove.
        asynchronous: false
        cache: false
    }

    // Insurance, not decoration. Against the shipped backdrop the ink already
    // measures 15:1 or better everywhere, so this is deliberately almost
    // nothing at the top and middle — it exists so that pointing
    // config.background at some bright photograph degrades to "slightly dim
    // photograph" instead of "unreadable clock". The stronger bottom stop does
    // do real work: the contour band is the brightest part of our own art and
    // the power controls sit on top of it.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.00; color: Qt.rgba(0.016, 0.027, 0.051, 0.10) }
            GradientStop { position: 0.45; color: Qt.rgba(0.016, 0.027, 0.051, 0.06) }
            GradientStop { position: 0.78; color: Qt.rgba(0.016, 0.027, 0.051, 0.14) }
            GradientStop { position: 1.00; color: Qt.rgba(0.016, 0.027, 0.051, 0.38) }
        }
    }

    // ============================================================== brand ==
    //
    // Small, high, and quiet. The mark is here so the owner knows what they are
    // logging in to on a machine that dual-boots, not to sell anything to
    // somebody who already bought it.
    Image {
        id: brand
        visible: config.showlogo === "shown" && status === Image.Ready && !root.compact
        source: config.logo
        y: Math.round(root.height * 0.072)
        anchors.horizontalCenter: parent.horizontalCenter
        // 52 was the first try and it was wrong: the mark is a rounded tile
        // with its own dark ground, and at that size the tile read as a smudge
        // rather than as a letter. 72 is the smallest size at which the D is
        // legibly a D on a 1080p screen — checked on the render, not guessed.
        width: root.px(72)
        height: root.px(72)
        fillMode: Image.PreserveAspectFit
        smooth: true
        opacity: 0.95
        Accessible.ignored: true
    }

    // ====================================================== edition badge ==
    //
    // One quiet line under the mark, and only on the edition that paid for
    // it. The text comes from theme.conf ([General] editionBadge) — the same
    // file-is-data pattern as showlogo and background above. The key ships
    // EMPTY, and 0600-pro-edition sets it to "PRO EDITION" on the Pro image,
    // so on free this element renders nothing and the login screen is exactly
    // the layout it was before this block existed.
    //
    // (config.editionBadge || "") and not config.editionBadge alone: SDDM
    // hands the theme undefined for a key theme.conf does not carry, and an
    // undefined text is a QML warning on every login. The fallback keeps a
    // missing key identical to an empty one.
    Text {
        id: editionBadge
        visible: text !== "" && !root.compact
        text: (config.editionBadge || "")
        anchors.top: brand.bottom
        anchors.topMargin: root.px(10)
        anchors.horizontalCenter: parent.horizontalCenter
        color: "#e8eef7"
        opacity: 0.85
        font.pixelSize: root.px(13)
        font.bold: true
        font.letterSpacing: root.px(3)
        Accessible.ignored: true   // decoration, like the mark it sits under
    }

    // ============================================================== clock ==
    //
    // Windows' shape: the time large, the date under it in full. Both come out
    // of the locale, so en_US gets "2:35 PM" and "Monday, July 27, 2026",
    // de_DE gets "14:35" and "Montag, 27. Juli 2026", and nothing here has to
    // know that.
    //
    // USE Date.toLocaleTimeString/toLocaleDateString, NOT Qt.formatTime and
    // Qt.formatDate. This is a trap and it is silent. Qt.formatDate(d,
    // Locale.LongFormat) looks locale-aware and is not: that overload takes a
    // Qt::DateFormat, Locale.LongFormat is 0, and Qt::TextDate is also 0 — so
    // it prints "Mon Jul 27 2026" on every machine on earth, English names and
    // English order, in German, in French, everywhere. Locale.ShortFormat is 1
    // and Qt::ISODate is 1, which is why the first cut of this file rendered
    // "14:35:25" on a US English machine that should have shown "2:35 PM". I
    // checked all five of C, en_GB, en_US, de_DE and fr_FR under qml6 before
    // and after; the Date methods below are right in all five.
    Column {
        id: clock
        visible: config.showClock === "true" && !root.compact
        y: Math.round(root.height * 0.17)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: root.px(2)

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.now.toLocaleTimeString(Qt.locale(), root.timeFormat)
            color: root.cInk
            font.pixelSize: root.px(76)
            font.weight: Font.Light
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.now.toLocaleDateString(Qt.locale(), Locale.LongFormat)
            color: root.cSoft
            font.pixelSize: root.px(20)
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }
    }

    // =========================================================== the form ==

    Column {
        id: form
        // 0.43, not centred. Windows puts the clock at about a third of the way
        // down and the sign-in below the middle, and the whole point of this
        // layout is that somebody who has used Windows for fifteen years does
        // not have to look for anything. Checked at 1024x768: the form ends 52
        // pixels above the power buttons, so nothing overlaps on the smallest
        // screen the product supports.
        y: Math.round(root.height * (root.compact ? 0.20 : 0.43))
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.px(440)
        spacing: root.px(14)

        // ------------------------------------------------------- the avatar
        //
        // A round avatar needs a round mask, and a round mask is the one thing
        // plain QtQuick does not have: `clip` is rectangular, and every other
        // route (OpacityMask, MultiEffect) is another QML module this theme has
        // promised not to depend on. Canvas is part of QtQuick itself, so the
        // mask costs an import of nothing.
        //
        // The circle underneath is not a placeholder for the placeholder's
        // sake: if the face file is missing, unreadable by the sddm user, or a
        // format Qt cannot decode, Canvas simply never fires imageLoaded and
        // there is no error signal to catch. The owner then sees their initial
        // in a brand-blue disc, which is a design, rather than a hole.
        Item {
            id: avatar
            width: root.px(104)
            height: root.px(104)
            anchors.horizontalCenter: parent.horizontalCenter

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "#1b3f63"
                border.width: root.px(2)
                border.color: Qt.rgba(0.58, 0.70, 0.84, 0.30)
                Text {
                    anchors.centerIn: parent
                    text: root.userInitial
                    color: root.cInk
                    font.pixelSize: root.px(44)
                    font.weight: Font.DemiBold
                    Accessible.ignored: true
                }
            }

            Canvas {
                id: face
                anchors.fill: parent
                visible: root.faceReady

                property string src: root.userIcon ? root.userIcon.toString() : ""

                onSrcChanged: face.reload()
                onWidthChanged: face.requestPaint()

                function reload() {
                    root.faceReady = false;
                    if (face.src === "")
                        return;
                    if (face.isImageLoaded(face.src)) {
                        root.faceReady = true;
                        face.requestPaint();
                    } else {
                        face.loadImage(face.src);
                    }
                }

                onImageLoaded: {
                    root.faceReady = true;
                    face.requestPaint();
                }

                onPaint: {
                    var ctx = face.getContext("2d");
                    ctx.reset();
                    if (face.src === "" || !face.isImageLoaded(face.src))
                        return;
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(face.width / 2, face.height / 2, face.width / 2, 0, 2 * Math.PI);
                    ctx.clip();
                    ctx.drawImage(face.src, 0, 0, face.width, face.height);
                    ctx.restore();
                }

                Component.onCompleted: face.reload()
            }

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "transparent"
                border.width: root.px(2)
                border.color: Qt.rgba(0.58, 0.70, 0.84, 0.30)
                visible: root.faceReady
            }
        }

        // --------------------------------------------------------- the name
        Text {
            visible: !root.anonymous
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.userLabel
            color: root.cInk
            font.pixelSize: root.px(30)
            font.weight: Font.DemiBold
            elide: Text.ElideRight
            Accessible.role: Accessible.StaticText
            Accessible.name: root.userLabel
        }

        // Only when there is no list to choose from. See `anonymous` above.
        Rectangle {
            id: nameBox
            visible: root.anonymous
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            height: root.px(60)
            radius: root.px(12)
            color: root.cField
            border.width: root.px(nameField.activeFocus ? 2 : 1)
            border.color: nameField.activeFocus ? root.cAccent : root.cEdge

            TextInput {
                id: nameField
                anchors.fill: parent
                anchors.leftMargin: root.px(18)
                anchors.rightMargin: root.px(18)
                verticalAlignment: TextInput.AlignVCenter
                enabled: !root.busy
                color: root.cInk
                font.pixelSize: root.px(20)
                selectByMouse: true
                selectionColor: root.cAccent
                selectedTextColor: "#06101c"
                activeFocusOnTab: true
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText

                Accessible.role: Accessible.EditableText
                Accessible.name: qsTr("User name")

                onAccepted: pw.forceActiveFocus()

                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    visible: nameField.text.length === 0
                    text: qsTr("User name")
                    color: root.cMuted
                    font.pixelSize: root.px(20)
                    Accessible.ignored: true
                }
            }
        }

        // ----------------------------------------------------- the password
        //
        // Declaration order in this file is the Tab order — Qt builds the focus
        // chain from the order items appear in the tree. Field, then Show, then
        // the arrow, then Switch user, then the bottom bar left to right. Get
        // that wrong and a keyboard user meets the shutdown button before the
        // password box, which is WCAG 2.4.3 in its plainest form.
        Rectangle {
            id: field
            visible: root.userNeedsPassword
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            height: root.px(60)
            radius: root.px(12)
            color: root.cField
            border.width: root.px(pw.activeFocus ? 2 : 1)
            border.color: pw.activeFocus ? root.cAccent : root.cEdge

            TextInput {
                id: pw
                anchors.left: parent.left
                anchors.leftMargin: root.px(18)
                anchors.right: showBtn.left
                anchors.rightMargin: root.px(8)
                anchors.verticalCenter: parent.verticalCenter
                enabled: !root.busy
                color: root.cInk
                font.pixelSize: root.px(20)
                echoMode: root.showPassword ? TextInput.Normal : TextInput.Password
                passwordMaskDelay: 0
                selectByMouse: true
                selectionColor: root.cAccent
                selectedTextColor: "#06101c"
                activeFocusOnTab: true
                inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoAutoUppercase
                                  | Qt.ImhNoPredictiveText

                Accessible.role: Accessible.EditableText
                Accessible.name: qsTr("Password")
                Accessible.description: qsTr("Type your password and press Enter")

                onAccepted: root.signIn()

                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    visible: pw.text.length === 0
                    text: root.busy ? qsTr("Signing in…") : qsTr("Password")
                    color: root.cMuted
                    font.pixelSize: root.px(20)
                    Accessible.ignored: true
                }
            }

            TextButton {
                id: showBtn
                anchors.right: goBtn.left
                anchors.rightMargin: root.px(6)
                anchors.verticalCenter: parent.verticalCenter
                quiet: true
                ink: root.cMuted
                visible: pw.text.length > 0
                label: root.showPassword ? qsTr("Hide") : qsTr("Show")
                hint: qsTr("Show or hide the password you have typed")
                onActivated: root.showPassword = !root.showPassword
            }

            // The mouse route to the same place Enter goes. Windows puts this
            // arrow inside the field and everybody arriving from Windows 10
            // knows what it is, which is the whole argument for it being here.
            Rectangle {
                id: goBtn
                anchors.right: parent.right
                anchors.rightMargin: root.px(8)
                anchors.verticalCenter: parent.verticalCenter
                width: root.px(44)
                height: root.px(44)
                radius: width / 2
                color: goArea.containsMouse || goBtn.activeFocus
                       ? root.cAccent : Qt.rgba(0.25, 0.66, 0.96, 0.22)
                border.width: 1
                border.color: root.cAccent
                activeFocusOnTab: true
                opacity: root.busy ? 0.5 : 1.0

                Accessible.role: Accessible.Button
                Accessible.name: qsTr("Sign in")
                Accessible.focusable: true
                Accessible.focused: goBtn.activeFocus
                Accessible.onPressAction: root.signIn()

                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                            || event.key === Qt.Key_Enter) {
                        root.signIn();
                        event.accepted = true;
                    }
                }

                FocusRing { ringRadius: goBtn.radius; on: goBtn.activeFocus }

                ArrowGlyph {
                    anchors.centerIn: parent
                    width: root.px(19)
                    height: root.px(19)
                    // The ink has to flip with the fill. At rest the disc is
                    // cAccent at 22% over the field, which composites to
                    // #132e46, and the pale arrow measures 12.9:1 on it. Hover
                    // or focus makes the disc SOLID cAccent, and the same pale
                    // arrow measures 2.38:1 there — below the 3:1 WCAG 1.4.11
                    // asks of a control's meaningful graphic, and it fails at
                    // exactly the moment somebody is aiming at it or has tabbed
                    // to it. Dark ink on the accent measures 7.5:1. Same
                    // inversion as selectedTextColor below and as the boot
                    // menu's selected entry: on Dagric blue, ink goes dark.
                    ink: (goArea.containsMouse || goBtn.activeFocus)
                         ? "#06101c" : root.cInk
                }

                MouseArea {
                    id: goArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        goBtn.forceActiveFocus(Qt.MouseFocusReason);
                        root.signIn();
                    }
                }
            }
        }

        // An account with no password still has to be able to get in, and a
        // password box that ignores whatever you type would be a cruel way to
        // find that out.
        TextButton {
            visible: !root.userNeedsPassword
            anchors.horizontalCenter: parent.horizontalCenter
            label: qsTr("Sign in")
            hint: qsTr("This account has no password")
            onActivated: root.signIn()
        }

        // --------------------------------------------------------- messages
        //
        // One line, one place. Caps Lock is a warning about the future; the
        // sign-in message is a report about the past. They are shown in the
        // same slot because they cannot both be the most useful thing to say,
        // and stacking them would push the form around as they come and go.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            height: root.px(24)
            text: keyboard.capsLock ? qsTr("Caps Lock is on") : root.message
            color: (keyboard.capsLock || root.messageIsWarning) ? root.cWarm : root.cSoft
            font.pixelSize: root.px(15)
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }

        TextButton {
            id: switchBtn
            visible: root.haveUserChoice
            anchors.horizontalCenter: parent.horizontalCenter
            quiet: true
            ink: root.cSoft
            label: qsTr("Other user")
            hint: qsTr("Sign in as somebody else on this computer")
            onActivated: {
                userSheet.visible = true;
                userList.forceActiveFocus();
            }
        }
    }

    // ========================================================= bottom bar ==

    // Left: the two pickers a Windows switcher will never need and a Linux user
    // will look for exactly where every other login screen puts them. Small,
    // grey, no border — present without asking for attention.
    Row {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: root.px(26)
        spacing: root.px(6)

        TextButton {
            visible: root.haveSessionChoice
            quiet: true
            ink: root.cMuted
            // %1 is the session name. A placeholder rather than a "+" join for
            // the same reason the first-run wizard uses one: a sentence glued
            // together in QML cannot be reordered by a translator, and not
            // every language puts the label before the value.
            label: qsTr("Desktop: %1").arg(sessions.count > root.sessionIndex && root.sessionIndex >= 0
                                  ? sessions.itemAt(root.sessionIndex).name : "")
            hint: qsTr("Choose which desktop to start")
            onActivated: {
                sessionSheet.visible = true;
                sessionList.forceActiveFocus();
            }
        }

        TextButton {
            visible: root.haveLayoutChoice
            quiet: true
            ink: root.cMuted
            // %1 is the layout's short name, e.g. "de". See the note above.
            label: qsTr("Keyboard: %1").arg(keyboard.layouts[keyboard.currentLayout]
                                   ? keyboard.layouts[keyboard.currentLayout].shortName : "")
            hint: qsTr("Choose the keyboard layout used to type your password")
            onActivated: {
                layoutSheet.visible = true;
                layoutList.forceActiveFocus();
            }
        }
    }

    // Right: power. Words, not symbols — "clearly labelled" is the requirement
    // and a power glyph is only clear to somebody who already knows it. Each is
    // hidden when logind says the machine cannot do it, rather than shown and
    // then silently doing nothing.
    Row {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: root.px(26)
        spacing: root.px(10)

        TextButton {
            visible: sddm.canReboot
            label: qsTr("Restart")
            hint: qsTr("Shut down and start the computer again")
            onActivated: sddm.reboot()
        }

        TextButton {
            visible: sddm.canPowerOff
            label: qsTr("Shut down")
            hint: qsTr("Turn the computer off")
            onActivated: sddm.powerOff()
        }
    }

    // ============================================================ sheets ==

    Sheet {
        id: userSheet
        title: qsTr("Who is signing in?")

        ListView {
            id: userList
            width: parent.width
            height: Math.min(users.count * root.px(52), root.height - root.px(190))
            model: userModel
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            currentIndex: root.userIndex

            delegate: SheetRow {
                required property int index
                required property string name
                required property string realName
                label: realName !== "" ? realName : name
                sub: realName !== "" ? "(" + name + ")" : ""
                current: index === root.userIndex
                onActivated: root.pickUser(index)
            }
        }
    }

    Sheet {
        id: sessionSheet
        title: qsTr("Which desktop should start?")

        ListView {
            id: sessionList
            width: parent.width
            height: Math.min(sessions.count * root.px(52), root.height - root.px(190))
            model: sessionModel
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            currentIndex: root.sessionIndex

            delegate: SheetRow {
                required property int index
                required property string name
                label: name
                current: index === root.sessionIndex
                onActivated: {
                    root.sessionIndex = index;
                    sessionSheet.visible = false;
                    pw.forceActiveFocus();
                }
            }
        }
    }

    Sheet {
        id: layoutSheet
        title: qsTr("Keyboard layout")

        ListView {
            id: layoutList
            width: parent.width
            height: Math.min(keyboard.layouts.length * root.px(52), root.height - root.px(190))
            model: keyboard.layouts
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            currentIndex: keyboard.currentLayout

            delegate: SheetRow {
                required property int index
                required property var modelData
                label: modelData.longName
                sub: modelData.shortName
                current: index === keyboard.currentLayout
                onActivated: {
                    keyboard.currentLayout = index;
                    layoutSheet.visible = false;
                    pw.forceActiveFocus();
                }
            }
        }
    }
}
