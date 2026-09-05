// SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
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
//
// ============================================================ ACCESSIBILITY
//
// This is the first screen every customer meets, so it is also the first place
// an inaccessible product gives itself away. Until this pass the window failed
// in the most complete way possible: a keyboard-only or screen-reader user
// could reach Back, Skip and Next — and NOT ONE of the choices the wizard
// exists to ask. Every card was a bare Rectangle with a MouseArea on it, which
// to an assistive technology is furniture, not a control. You could walk
// through the wizard; you could not answer it.
//
// Five things were wrong, and each needed a different fix:
//
//  1. NOTHING HAD A ROLE. Qt only builds an accessible object for an Item once
//     Accessible.role is set. A Rectangle without one is invisible to Orca —
//     not badly labelled, absent. Every control below now declares role, name
//     and state, and every decorative shape declares Accessible.ignored so the
//     tree stays readable instead of drowning in anonymous boxes.
//
//  2. NOTHING WAS TABBABLE. Item.activeFocusOnTab defaults to FALSE, so custom
//     controls are skipped by Tab unless you opt in. Qt Quick Controls buttons
//     opt in for you; Rectangles do not. That single default is why only the
//     three real Buttons were reachable.
//
//  3. MouseArea IS NOT AN ACTIVATION PATH. It contributes nothing to the
//     accessibility tree, so a screen reader has no way to press the thing it
//     is describing. Everything clickable now answers Accessible.onPressAction
//     and Space/Enter as well as the mouse, all routed to the same handler so
//     the three can never drift apart.
//
//  4. FOCUS WAS INVISIBLE. Even where focus could land there was nothing to
//     see, and the obvious fix — one coloured ring — is a trap here, because
//     the wallpaper tiles are photographs. A light ring vanishes on snow, a
//     dark one vanishes on a night sky. FocusRing below draws BOTH, one inside
//     the other, so whatever the tile is showing, one of the two strokes has
//     contrast against it.
//
//  5. THE COLOURS WERE NOT MEASURED. Light mode shipped white-on-#3fa9f5 for
//     the Next button — 2.56:1, where WCAG AA wants 4.5:1 — and the same
//     accent as body text on white, 2.56:1. Dark mode passed comfortably,
//     which is exactly how it went unnoticed: whoever eyeballed it was looking
//     at the dark build. Nothing is eyeballed now. onColor() and readable()
//     below compute the ink from the real relative-luminance formula, so the
//     numbers hold for accent colours that do not exist yet as well as the
//     five in the catalogue today.
//
// The remaining rule is negative and just as important: DO NOT FIGHT THE
// SCREEN READER. This window never grabs focus on a timer, never moves focus
// as an animation lands, and never re-focuses itself when a value changes. The
// one thing it does on a step change is Accessible.announce(), which speaks
// the new step politely and leaves the user's focus exactly where they left it.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: app

    visible: true
    // Fullscreen, frameless, like the out-of-box experience this audience just
    // left. Two things follow and both are deliberate:
    //   * there is no title bar and therefore no window close button. The exit
    //     is the wizard's own "I'll do this later", which is the escape hatch
    //     that must never be removed — a first run someone cannot leave is a
    //     first run someone force-reboots out of.
    //   * anything launched from INSIDE the wizard would open behind this
    //     window and be invisible. Two answers, for two kinds of launch: the
    //     downloads step QUEUES its installs and runs them at Finish, after
    //     this window is gone — and every run() helper (text size, migration,
    //     the finish links) DROPS THE WIZARD TO WINDOWED first, because those
    //     are interactive mid-wizard by design and cannot be deferred. See
    //     run() for why the drop is one-way.
    // width/height below are kept as the fallback geometry for a window
    // manager that refuses fullscreen.
    visibility: Window.FullScreen
    width: 1060
    height: 720
    // These used to be 760x560. That is bigger than the whole desktop once a
    // 1024x768 machine is set to 150% text — 683x512 in layout terms — and the
    // window then hangs off the bottom with the Next button underneath the
    // screen edge. The owner who most needs large text was the one owner who
    // could not finish the wizard. Every page scrolls now (see Page), so a
    // small window is cramped rather than broken, and the minimum can be the
    // smallest thing that still reads.
    minimumWidth: 560
    minimumHeight: 420
    title: app.windowTitle
    color: app.cBg

    // --- the catalogue -------------------------------------------------------
    property string edition: "free"
    property string editionName: "Dagric OS"
    // The wizard's own name, used by the title bar (which is also what the
    // taskbar shows) and by the header heading, so the two can never say
    // different things. Free keeps the exact string every reference to this
    // window uses — the launcher entry, the manual, the "run Set Up Dagric
    // again" hint in the goodbye popup. Pro appends its mark as a plain
    // suffix rather than through a second msgid, so the two editions can
    // never drift apart in translation: "Pro" is a product name and stays
    // untranslated by the same rule as "Dagric" itself, and the shell side
    // (dagric-firstrun's TITLE, used by every kdialog fallback) builds the
    // identical string the identical way.
    // app.t, not bare t: tools/i18n-wizard.py extracts what this file asks
    // for with the pattern app\.(?:t|tf)\( — a bare t() call is invisible to
    // it, the shell's matching STRINGS line then looks orphaned, and the
    // build stops. Found by the gate doing exactly that.
    readonly property string windowTitle: edition === "pro"
                                          ? app.t("Set Up Dagric") + " — Pro"
                                          : app.t("Set Up Dagric")
    property bool live: false
    property bool reducedMotion: false
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
    // What the machine looked like when setup opened. Filled in once the
    // catalogue arrives; see undoAll().
    property string startMode: "light"
    property string startWallId: ""
    property int startScale: 100
    // The accent the machine wore when setup opened. "" and the brand blue
    // are what a fresh install reports, because nothing ships an AccentColor.
    property string startAccentId: ""
    property color startAccent: "#ff3b5c"
    property string accentId: ""
    property string wallId: ""
    property int scale: 0
    property string layoutId: ""
    property bool changed: false
    property var touched: ({})

    // --- honouring the desktop's own text size -------------------------------
    // EN 301 549 clause 11.7 and Section 508 503.2 both say the same thing in
    // different words: an application must permit the user preferences the
    // platform already offers for colour, contrast, font type and FONT SIZE.
    // Every size in this file used to be a hard number, so a person who had
    // gone into System Settings and asked for larger text got a wizard that
    // ignored them completely — the one window where being ignored matters
    // most, because it is the window that offers to set the text size.
    //
    // FontMetrics with no font of its own reports the real application font,
    // which is where Plasma's font preference and any font-DPI setting both
    // land. ~15px tall is an ordinary 10pt desktop font, so that is 1.0 and
    // today's design is untouched; asking for 150% text makes this 1.5 and the
    // whole window grows with it. Capped, because past a point the answer is
    // to scroll (which every page now does) rather than to keep inflating.
    // The window's words, looked up by their own English text.
    //
    // dagric-firstrun sends a "strings" map in the catalogue, already through
    // gettext in the owner's language. t() returns the translation when there
    // is one and the key otherwise — and the key IS the English sentence, so a
    // language with no catalogue, a string added since the last extraction, or
    // a catalogue that failed to load all degrade to correct English rather
    // than to an identifier. There is no state in which this shows a developer
    // string to a customer.
    property var strings: ({})
    function t(s) {
        var v = app.strings[s];
        return (v === undefined || v === "") ? s : v;
    }

    // Same lookup, then substitute. %1 and %2 rather than string concatenation,
    // because a sentence built by "+" fixes English word order into the code:
    // "Welcome to " + name + "." has nowhere for a language that puts the name
    // first to go, and "Step 1 of 5" is "Schritt 1 von 5" but "Étape 1 sur 5".
    // The placeholders are %1/%2 and not %s so that a translator can reorder
    // them, and so xgettext never mistakes these for C format strings.
    function tf(s, a, b) {
        var v = app.t(s);
        v = v.replace("%1", a === undefined ? "" : a);
        return b === undefined ? v : v.replace("%2", b);
    }

    FontMetrics { id: sysFont }
    property real ui: Math.max(1.0, Math.min(1.9, sysFont.height / 15.0))
    function px(n) { return Math.round(n * app.ui); }
    function motionMs(n) { return app.reducedMotion ? 0 : n; }

    // Short window: shrink the decoration, not the words.
    //
    // Every page can scroll now, which is the right safety net and the wrong
    // first impression — a scrollbar on the welcome screen says "this did not
    // fit" before the owner has read a word. It showed up on an ordinary
    // 1024x768 VM, where the window clamps to about 860x635 and the welcome
    // page's 88px logo and generous gaps are just past what is left after the
    // header and footer take their share.
    //
    // 700 AND NOT 660, because 660 missed the commonest machine there is. A
    // 1024x768 desktop with a Plasma panel on it leaves 724 usable, so this
    // window opens 984x684 — not "short" by the old number, so every trim below
    // stayed switched off while the finish page ran 40px past the bottom and
    // the appearance page ran 8px past it. 700 is the largest useful number
    // that still leaves the 1060x720 default alone: the design size must not
    // get the cramped layout, and at 720 nothing needs it.
    //
    // Measured under Xvfb at the four sizes this window actually opens at —
    // 984x720, 984x684, 860x635 and 760x560 — rather than reasoned about.
    //
    // So the big decorative elements stand down when there is no room for them.
    // The heading, the body text and the note are untouched at every size: the
    // logo is there to be handsome and the sentences are there to be read, and
    // when those two compete the sentences win.
    readonly property bool shortWin: app.height < app.px(700)

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
    property color cAccent: "#ff3b5c"

    // --- contrast, computed rather than guessed ------------------------------
    // WCAG 2.x relative luminance and contrast ratio, straight from the spec.
    // These exist because the accent is not ours to choose: it comes out of the
    // catalogue, the owner picks it mid-wizard, and a future release can add
    // one. A hand-picked "text colour that looks right on blue" is only right
    // until somebody clicks Amber. Deriving it means every accent that ever
    // ships is legible by construction.
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

    // The two inks have to be color OBJECTS, not string literals, and that is
    // the whole bug this pair of properties exists to fix. lumOf reads c.r, c.g
    // and c.b — a JavaScript string has none of those, so each one came back
    // undefined, the arithmetic produced NaN, and the comparison below was
    // `NaN >= NaN`, which is false. onColor therefore returned the dark ink
    // every single time, on every accent, forever. It read like a computation
    // and behaved like a constant, which is why it survived review: the light
    // accents it was tested against wanted dark ink anyway. Pick a deep accent
    // and the wizard drew dark text on a dark fill.
    readonly property color inkLight: "#ffffff"
    readonly property color inkDark:  "#101a26"

    // Ink for text sitting ON a filled patch of `bg` — black or white,
    // whichever wins. Both are checked; no assumption about which way is
    // "lighter", because a pale accent and a deep one need opposite answers.
    function onColor(bg) {
        return app.ratioOf(app.inkLight, bg) >= app.ratioOf(app.inkDark, bg)
               ? app.inkLight : app.inkDark;
    }

    // Walk `fg` away from `bg` until it clears `need`, keeping its hue. Used
    // for the accent as TEXT and as a component boundary, which are the two
    // places a mid-tone brand colour reliably fails. The loop is bounded: a
    // colour that cannot get there (pure black on black) stops rather than
    // spins, and returns the best it managed.
    function readable(fg, bg, need) {
        var c = fg;
        var up = app.lumOf(bg) < 0.18;
        for (var i = 0; i < 24 && app.ratioOf(c, bg) < need; i++)
            c = up ? Qt.lighter(c, 1.10) : Qt.darker(c, 1.10);
        return c;
    }

    // Text on the accent (button labels, the step number in the rail).
    readonly property color cOnAccent: app.onColor(app.cAccent)
    // The accent used AS text, per background. 1.4.3 Contrast, AA, 4.5:1.
    readonly property color cInkPanel:  app.readable(app.cAccent, app.cPanel, 4.5)
    readonly property color cInkPanel2: app.readable(app.cAccent, app.cPanel2, 4.5)
    readonly property color cInkBg:     app.readable(app.cAccent, app.cBg, 4.5)
    // Borders of interactive cards, against BOTH surfaces they are drawn on.
    //
    // The theme and text-size cards are filled with cPanel, but the wallpaper
    // and taskbar tiles are transparent, so their border sits on the page
    // background instead. Deriving against cPanel alone measured 3.0:1 on a
    // card and 2.72:1 on the page — a fail, on exactly the tiles where the
    // border is the ONLY thing drawing the card. Chaining the two pushes the
    // colour until it clears 3:1 on whichever it lands on. The direction is
    // the same for both (in light mode both backgrounds are pale, in dark mode
    // both are near-black), so the second pass only ever tightens the first.
    //
    // cLine is deliberately left alone: it draws the header rule and the rail
    // divider, which are decoration rather than components, and 1.4.11 does
    // not reach them. Turning every hairline into a 3:1 stroke would make the
    // wizard look like a spreadsheet for no accessibility gain.
    readonly property color cSelect: app.readable(app.readable(app.cAccent, app.cPanel, 3.0),
                                                  app.cBg, 3.0)
    readonly property color cEdge: app.readable(app.readable(app.cLine, app.cPanel, 3.0),
                                                app.cBg, 3.0)

    Behavior on cBg     { ColorAnimation { duration: app.motionMs(200) } }
    Behavior on cPanel  { ColorAnimation { duration: app.motionMs(200) } }
    Behavior on cPanel2 { ColorAnimation { duration: app.motionMs(200) } }
    Behavior on cLine   { ColorAnimation { duration: app.motionMs(200) } }
    Behavior on cText   { ColorAnimation { duration: app.motionMs(200) } }
    Behavior on cDim    { ColorAnimation { duration: app.motionMs(200) } }
    Behavior on cAccent { ColorAnimation { duration: app.motionMs(200) } }

    function send(msg) {
        console.log("@DAGRIC@" + msg);
    }

    // Speak something without moving anybody's focus. Politeness matters: this
    // queues behind whatever Orca is already saying instead of cutting the user
    // off mid-word. Guarded because announce() arrived in Qt 6.8 and a wizard
    // that throws on an older runtime is worse than one that stays quiet.
    function say(msg) {
        try {
            if (typeof pageArea.Accessible.announce === "function")
                pageArea.Accessible.announce(msg, Accessible.Polite);
        } catch (e) {
            // No announcement channel here. Silence is the correct fallback.
        }
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
                app.reducedMotion = d.reducedMotion === true;
                app.scaleMode = d.scaleMode ? d.scaleMode : "none";
                app.currentScale = d.currentScale ? d.currentScale : 0;
                app.hasDisplayTool = d.hasDisplayTool === true;
                app.strings = d.strings ? d.strings : ({});
                app.hasWindows = d.hasWindows === true;
                app.wallpapers = d.wallpapers ? d.wallpapers : [];
                app.accents = d.accents ? d.accents : [];
                app.layouts = d.layouts ? d.layouts : [];
                // Start from what is already on screen, so the tiles show the
                // truth on arrival rather than pretending nothing is set.
                app.mode = (d.currentMode === "dark") ? "dark" : "light";
                app.wallId = d.currentWall ? d.currentWall : "";
                app.scale = app.currentScale;
                app.accentId = d.currentAccent ? d.currentAccent : "";
                if (d.currentAccentHex)
                    app.cAccent = d.currentAccentHex;
                // Remember where we came in, so "Undo my changes" can put the
                // WINDOW back too and not just the desktop. Captured here
                // rather than in undoAll(), because by then it is long gone.
                app.startMode = app.mode;
                app.startWallId = app.wallId;
                app.startScale = app.scale;
                app.startAccentId = app.accentId;
                // From the catalogue, NOT from app.cAccent. cAccent has a
                // Behavior/ColorAnimation on it, so reading it back on the line
                // after assigning it returns the value it is animating AWAY
                // from — capturing it here would have stored the brand blue and
                // undo would have looked fixed while doing exactly what it did
                // before. Caught by running the window headless and printing
                // the accent after Undo.
                if (d.currentAccentHex)
                    app.startAccent = d.currentAccentHex;
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
    //
    // The three catalogue-failure messages are the only user-facing strings in
    // this file that stay English literals, and deliberately: the catalogue is
    // where the translations live, so a message about the catalogue not loading
    // is by definition a message no translation is available for. Wrapping them
    // in app.t() would look correct and return the English key anyway.
    Timer {
        interval: 4000
        running: true
        repeat: false
        onTriggered: {
            if (!app.loaded && app.loadError === "") {
                app.loadError = "The setup catalogue could not be read.";
                app.say(app.loadError);
            }
        }
    }

    // --- the steps -----------------------------------------------------------
    property var steps: ["welcome", "finish"]
    property int stepIndex: 0
    readonly property string step: (app.stepIndex >= 0 && app.stepIndex < app.steps.length)
                                   ? app.steps[app.stepIndex] : "welcome"

    // Say the new step out loud. A sighted user sees the whole page change; a
    // screen-reader user got nothing at all, because pressing Next moved them
    // to a page that never announced itself. Polite, and focus is untouched.
    onStepChanged: app.say(app.stepTitle(app.step) + ". "
                           + app.tf("Step %1 of %2", app.stepIndex + 1, app.steps.length) + ".")

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
        // Always offered, live included: on the live stick the step carries
        // its own warning that additions vanish at shutdown, and hiding the
        // step entirely would hide the one place the trial can show off the
        // one-click apps.
        s.push("downloads");
        s.push("finish");
        app.steps = s;
        app.stepIndex = 0;
    }

    // Translated, because this one function feeds three places at once: the step
    // rail down the left, the "Step 2 of 5, How it looks" name the screen reader
    // reads, and the announcement on every step change. It used to return bare
    // English literals, so a German owner met a German desktop and an English
    // sidebar — with the German already sitting unused in the catalogue.
    function stepTitle(id) {
        switch (id) {
        case "welcome":    return app.t("Welcome");
        case "appearance": return app.t("How it looks");
        case "display":    return app.t("Text size");
        case "taskbar":    return app.t("The taskbar");
        case "files":      return app.t("Your files");
        case "downloads":  return app.t("Add your apps");
        case "finish":     return app.t("You're ready");
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

    // markVisited — earn the rail's tick WITHOUT arming "Undo my changes".
    //
    // For the two steps that hand the work to another program. The Undo button
    // restores exactly four things, and says so in its own description:
    // colours, wallpaper, text size, taskbar. It was nonetheless being armed by
    // two acts that live outside that set:
    //
    //   * "Choose a text size" launches dagric-display, which owns the scale
    //     and carries its own Keep/Revert with a twenty-second self-restore.
    //     The wizard deliberately records no scale baseline when that helper is
    //     driving (see dagric-firstrun), so there was nothing to put back.
    //   * "Bring files from Windows" launches dagric-migrate, which COPIES
    //     FILES. A file migration has no undo, and must not appear to.
    //
    // Offering Undo after either one is a promise the button cannot keep, and
    // the worse reading is the one a nervous switcher takes: that pressing it
    // might delete the documents they just copied across.
    function markVisited(id) {
        var t = app.touched;
        t[id] = true;
        app.touched = t;      // same reassign idiom; QML misses in-place edits
    }

    // --- the downloads step's queue ------------------------------------------
    // Names only ever LEAVE this window as a comma list the shell re-validates
    // against its own whitelist; ticking a card installs nothing here. The
    // installs run at Finish, after this fullscreen window is gone — a konsole
    // opened mid-wizard would be invisible behind it. markVisited, not
    // markTouched: a queued download is not one of the four things "Undo my
    // changes" can put back, so it must not arm that button.
    property var appsPicked: []
    property bool proPicked: false

    function toggleApp(id) {
        var a = app.appsPicked.slice();
        var i = a.indexOf(id);
        if (i >= 0) a.splice(i, 1); else a.push(id);
        app.appsPicked = a;   // reassign; QML misses in-place edits
        app.send("APPS|" + a.join(","));
        app.markVisited("downloads");
    }

    function toggleProUpgrade() {
        app.proPicked = !app.proPicked;
        app.send("TOPRO|" + (app.proPicked ? "1" : "0"));
        app.markVisited("downloads");
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
    // Each of these ends with app.say(). Applying a theme is a state change the
    // sighted owner sees instantly — the whole desktop repaints — and that a
    // screen-reader user would otherwise have to infer from silence. EN 301 549
    // 11.5.2.15 calls this change notification; in plain terms, if the machine
    // just did something, say so.
    function pickMode(m) {
        if (m !== "light" && m !== "dark")
            return;
        app.mode = m;
        app.markTouched("appearance");
        app.send("MODE|" + m);
        app.say(m === "dark" ? app.t("Dark theme applied.")
                             : app.t("Light theme applied."));
    }

    function pickAccent(a) {
        app.accentId = a.id;
        app.cAccent = a.hex;
        app.markTouched("appearance");
        app.send("ACCENT|" + a.id);
        app.say(app.tf("%1 highlight colour applied.", a.name));
    }

    function pickWall(w) {
        app.wallId = w.id;
        app.markTouched("appearance");
        app.send("WALL|" + w.id);
        app.say(app.tf("%1 wallpaper applied.", w.name));
    }

    function pickScale(v) {
        app.scale = v;
        app.markTouched("display");
        app.send("SCALE|" + v);
        app.say(app.tf("Text size set to %1 percent.", v));
    }

    function pickLayout(l) {
        app.layoutId = l.id;
        app.markTouched("taskbar");
        app.send("LAYOUT|" + l.id);
        app.say(app.tf("%1 taskbar applied.", l.name));
    }

    function run(what) {
        // Leaving fullscreen is part of running a helper, not an option. Three
        // pre-existing sites spawn windows mid-wizard — the text-size tool
        // (whose try-a-size dialog AUTO-REVERTS in twenty seconds if its Keep
        // button is not pressed), the migration konsole (whose page says
        // "carry on here while it works"), and the four finish links — and a
        // fullscreen, frameless wizard would sit exactly on top of every one
        // of them. The first review of this change shipped that bug with a
        // comment claiming it could not happen.
        //
        // Windowed, not Minimized, and deliberately NOT restored afterwards:
        // the migration page promises the owner can keep using the wizard
        // beside the helper, and snapping back to fullscreen on refocus would
        // re-hide a helper window that is still open. The immersive first run
        // lasts until the owner opens a tool; from then on the wizard behaves
        // like an ordinary window, which is what sharing a screen requires.
        if (app.visibility === Window.FullScreen)
            app.visibility = Window.Windowed;
        app.send("RUN|" + what);
    }

    function undoAll() {
        app.send("UNDO");
        app.changed = false;
        app.touched = ({});
        app.layoutId = "";
        // Put the WINDOW back as well, not only the desktop.
        //
        // Found by clicking it in a booted VM: choosing Dark and then "Undo my
        // changes" restored the desktop and the taskbar to light, said "Your
        // desktop is back the way it was", and left the wizard itself sitting
        // there in dark. The window wears whatever mode is being tried on (see
        // the `dark` property), and undo reset everything about the choice
        // except the choice itself — so the one screen making the promise was
        // the one visibly contradicting it.
        //
        // The shell has already restored the real settings by this point; these
        // lines only bring the window's own appearance and its selected tiles
        // back into agreement with them.
        app.mode = app.startMode;
        app.wallId = app.startWallId;
        app.scale = app.startScale;
        // The accent was the one thing this list missed. undoAll() used to
        // reset it to the brand blue literal, so an owner who had chosen amber
        // before running setup got their amber desktop back with a blue wizard
        // sitting on top of it — the shell restores the REAL AccentColor from
        // its capture file, and the window was contradicting it.
        app.accentId = app.startAccentId;
        app.cAccent = app.startAccent;
        app.say(app.t("Your desktop is back the way it was."));
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

    // A focus indicator that cannot be lost against its background.
    //
    // One ring in one colour is the usual answer and it is wrong here. Half the
    // controls on the appearance step are photographs — a white ring disappears
    // into an Arctic wallpaper and a dark one disappears into a night sky, and
    // an invisible focus ring is exactly as useful as no focus ring. So draw
    // two, one just outside the other: whatever the pixels underneath happen to
    // be, they cannot be simultaneously close to white and close to black, so
    // one of the two strokes always has contrast. It also means the indicator
    // does not depend on the accent colour, which the owner is busy changing.
    //
    // Drawn OUTSIDE the control's own border (negative margins) so it reads as
    // "focused" rather than fighting the "selected" border for the same pixels.
    component FocusRing: Item {
        id: fr
        property real ringRadius: 12
        property bool on: false
        anchors.fill: parent
        visible: fr.on
        z: 40

        Rectangle {                        // outer: light
            anchors.fill: parent
            anchors.margins: -app.px(4)
            radius: fr.ringRadius + app.px(4)
            color: "transparent"
            border.width: app.px(2)
            border.color: "#ffffff"
        }
        Rectangle {                        // inner: dark
            anchors.fill: parent
            anchors.margins: -app.px(2)
            radius: fr.ringRadius + app.px(2)
            color: "transparent"
            border.width: app.px(2)
            border.color: "#0a0f16"
        }
    }

    // Return and Enter, on every button in the wizard.
    //
    // Qt Quick's Button accepts Space and nothing else — Return only works for
    // the "default button" of a Dialog, which this window has none of. So a
    // keyboard user could Tab to Next and press Enter and NOTHING HAPPENED, on
    // every screen. That is not an obscure key: it is the key a Windows user
    // has pressed to mean "go on then" for twenty years, and this wizard's
    // whole promise is that the machine behaves the way they expect. It also
    // made the wizard inconsistent with itself, because the cards below do
    // take Enter. All three button styles get the same two lines.
    component Primary: Button {
        id: pb
        implicitHeight: app.px(40)
        implicitWidth: Math.max(app.px(120), pbText.implicitWidth + app.px(44))
        Keys.onReturnPressed: function(event) { pb.clicked(); event.accepted = true; }
        Keys.onEnterPressed:  function(event) { pb.clicked(); event.accepted = true; }
        scale: pb.down ? 0.98 : (pb.hovered ? 1.01 : 1.0)
        Behavior on scale {
            NumberAnimation { duration: app.motionMs(90); easing.type: Easing.OutCubic }
        }
        // Controls give a Button its role and name from `text` for free, which
        // is why Back/Skip/Next were the only things Orca could ever see here.
        // The description is the part `text` cannot carry: "Next" alone does
        // not say where next goes.
        // Compared against the TRANSLATED label, not the English one. The button
        // now says "Weiter", so a `pb.text === "Next"` test would silently never
        // match again and the description would vanish in every language but
        // English — a regression only a screen-reader user would ever find.
        Accessible.description: pb.text === app.t("Next") ? app.t("Go to the next step")
                              : (pb.text === app.t("Finish")
                                 ? app.t("Close setup and start using Dagric") : "")
        background: Rectangle {
            radius: app.px(9)
            color: pb.down ? Qt.darker(app.cAccent, 1.25)
                           : (pb.hovered ? Qt.lighter(app.cAccent, 1.08) : app.cAccent)
            Behavior on color { ColorAnimation { duration: app.motionMs(100) } }
            // Overriding `background` throws away the style's own focus visual.
            // That is easy to miss because the button still works — it is only
            // the person who cannot use a mouse who ever finds out.
            FocusRing { ringRadius: app.px(9); on: pb.activeFocus }
        }
        contentItem: Text {
            id: pbText
            text: pb.text
            color: app.cOnAccent
            font.pixelSize: app.px(14)
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Accessible.ignored: true       // the Button already carries the name
        }
    }

    component Ghost: Button {
        id: gb
        implicitHeight: app.px(40)
        implicitWidth: Math.max(app.px(110), gbText.implicitWidth + app.px(40))
        Keys.onReturnPressed: function(event) { gb.clicked(); event.accepted = true; }
        Keys.onEnterPressed:  function(event) { gb.clicked(); event.accepted = true; }
        scale: gb.down ? 0.98 : (gb.hovered ? 1.01 : 1.0)
        Behavior on scale {
            NumberAnimation { duration: app.motionMs(90); easing.type: Easing.OutCubic }
        }
        Accessible.description: gb.text === app.t("Back")
                                ? app.t("Go back to the previous step") : ""
        background: Rectangle {
            radius: app.px(9)
            color: (gb.down || gb.hovered) ? app.cPanel2 : "transparent"
            Behavior on color { ColorAnimation { duration: app.motionMs(100) } }
            border.width: 1
            border.color: app.cEdge
            FocusRing { ringRadius: app.px(9); on: gb.activeFocus }
        }
        contentItem: Text {
            id: gbText
            text: gb.text
            color: app.cText
            font.pixelSize: app.px(14)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Accessible.ignored: true
        }
    }

    component Quiet: Button {
        id: qb
        implicitHeight: app.px(34)
        implicitWidth: qbText.implicitWidth + app.px(18)
        Keys.onReturnPressed: function(event) { qb.clicked(); event.accepted = true; }
        Keys.onEnterPressed:  function(event) { qb.clicked(); event.accepted = true; }
        background: Item {
            // A borderless button needs its focus ring MORE than a solid one,
            // not less: there is no shape at all to tell you where you are.
            FocusRing { ringRadius: app.px(7); on: qb.activeFocus }
        }
        contentItem: Text {
            id: qbText
            text: qb.text
            // Underline on focus as well as hover. Hover is a mouse-only cue,
            // so the keyboard user was reading the same flat grey text whether
            // they were on it or not.
            color: (qb.hovered || qb.activeFocus) ? app.cText : app.cDim
            font.pixelSize: app.px(13)
            font.underline: qb.hovered || qb.activeFocus
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Accessible.ignored: true
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
        spacing: app.px(6)
        Text {
            Layout.fillWidth: true
            text: ph.heading
            color: app.cText
            font.pixelSize: app.px(27)
            font.bold: true
            wrapMode: Text.WordWrap
            // Big and bold is a sighted reader's cue that this is the heading.
            // Orca has no way to see "big and bold"; it needs to be told. With
            // a real heading role a screen-reader user can jump straight to it
            // instead of arrowing through the page to find out where they are.
            Accessible.role: Accessible.Heading
            Accessible.name: ph.heading
        }
        Text {
            Layout.fillWidth: true
            text: ph.sub
            visible: text !== ""
            color: app.cDim
            font.pixelSize: app.px(14)
            wrapMode: Text.WordWrap
            Accessible.role: Accessible.StaticText
            Accessible.name: ph.sub
        }
    }

    // Every step's content lives in one of these.
    //
    // It exists for one reason: a wizard whose Next button is below the bottom
    // of the screen is a wizard nobody can finish. That is not hypothetical —
    // it is what a 1024x768 machine at 150% text does, and large text is the
    // setting chosen by precisely the people who can least afford a broken
    // first screen. contentHeight is the LARGER of the viewport and what the
    // page actually needs, so when there is room the layout is exactly as it
    // always was (the fillHeight spacers still centre things), and when there
    // is not, the page scrolls instead of clipping.
    component Page: Flickable {
        id: pg
        property string label: ""
        property bool active: false
        // 24 rather than 34 on a short window, top and bottom, so a page that
        // overflows by a hair does not earn a scrollbar. Padding is the right
        // knob because it costs no information at all, and it fixes every page
        // rather than the one that happened to be measured.
        //
        // TWO properties and not one, and this is the whole point: the previous
        // round wrote the trim as `pad: app.px(shortWin ? 24 : 34)` right here
        // — and four of the six pages set `pad: app.px(40)` at their use site,
        // which is a plain override that threw the condition away. The trim
        // shipped, the welcome page was one of the four, and it never lost a
        // single pixel. `padWide` is the only knob a page is offered now, so
        // raising it cannot switch the short-window case off.
        property real padWide: 34
        property real pad: app.px(app.shortWin ? 24 : pg.padWide)
        default property alias body: pgCol.data

        anchors.fill: parent
        visible: pg.active || pg.opacity > 0.01
        enabled: pg.active
        opacity: pg.active ? 1.0 : 0.0
        scale: pg.active ? 1.0 : 0.985
        transformOrigin: Item.Center
        Behavior on opacity {
            NumberAnimation { duration: app.motionMs(170); easing.type: Easing.OutCubic }
        }
        Behavior on scale {
            NumberAnimation { duration: app.motionMs(190); easing.type: Easing.OutCubic }
        }
        clip: true
        contentWidth: pg.width
        contentHeight: Math.max(pg.height, pgCol.implicitHeight + pg.pad * 2)
        boundsBehavior: Flickable.StopAtBounds
        // Keyboard scrolling for the page itself, so a long page is reachable
        // without a mouse wheel. It is deliberately NOT a tab stop: the
        // controls inside are what people want to reach, and arrow keys scroll
        // whenever focus is somewhere on the page.
        flickableDirection: Flickable.VerticalFlick

        Accessible.role: Accessible.Grouping
        Accessible.name: pg.label
        Accessible.ignored: !pg.active

        // AlwaysOff, not AsNeeded, and this line is the actual bug everyone
        // was looking at.
        //
        // Replacing `contentItem` throws away the style's own thumb — and the
        // style's thumb is TRANSPARENT until the view is moving or hovered.
        // This Rectangle has no such fade, so under AsNeeded it was painted at
        // full strength on every page from the first frame, whether the page
        // overflowed or not. The welcome screen wore a grey bar down its right
        // edge, filling the whole track because the page fitted exactly — the
        // precise "this did not fit" signal that two rounds of logo-trimming
        // went looking for in the content height, where it never was.
        //
        // So the bar's existence is decided by the only thing that means
        // anything: whether there is something below the fold.
        ScrollBar.vertical: ScrollBar {
            policy: pg.contentHeight > pg.height ? ScrollBar.AlwaysOn
                                                 : ScrollBar.AlwaysOff
            contentItem: Rectangle {
                implicitWidth: app.px(6)
                radius: app.px(3)
                color: app.cEdge
            }
        }

        ColumnLayout {
            id: pgCol
            x: pg.pad
            y: pg.pad
            width: pg.width - pg.pad * 2
            height: pg.contentHeight - pg.pad * 2
            // The gaps between a page's blocks, trimmed with the padding and
            // for the same reason: five gaps at 18 is 90px of a 487px viewport,
            // and 13 still reads as separate blocks rather than a wall of text.
            spacing: app.px(app.shortWin ? 13 : 18)
        }
    }

    // A selectable card. Used for light/dark, text size, the taskbar layouts
    // and the finish links.
    //
    // This one component is the difference between a wizard a blind person can
    // answer and one they can only skip. Before this pass it was a Rectangle
    // and a MouseArea: no role, no name, no state, no focus, no way in.
    component Choice: Rectangle {
        id: ch
        property bool selected: false
        // What the control IS, said in words, because there is nothing here to
        // read: the card's meaning lives in a picture and a couple of labels
        // that belong to child items, and Qt will not assemble a name out of
        // those. Every use site sets this.
        property string label: ""
        property string hint: ""
        // Radio when it is one-of-a-set (light OR dark, one text size, one
        // taskbar); plain button when it just does something (the finish
        // links). Getting this wrong makes Orca promise a choice that is not
        // there, or hide one that is.
        property bool exclusive: true
        // And checkbox when it is many-of-a-set (the downloads step): a toggle
        // that is not one-of anything. Without this third role the apps cards
        // would announce as plain buttons and Orca would never say whether one
        // is ticked.
        property bool checkbox: false
        // False inside a grid, where the grid owns the single tab stop and the
        // arrow keys move between cards. Twenty wallpapers must not be twenty
        // stops on the way to Next.
        property bool tabbable: true
        signal clicked()

        radius: app.px(12)
        color: chMouse.containsMouse ? app.cPanel2 : app.cPanel
        scale: chMouse.pressed ? 0.99 : (chMouse.containsMouse ? 1.01 : 1.0)
        border.width: ch.selected ? 2 : 1
        border.color: ch.selected ? app.cSelect : app.cEdge
        Behavior on color { ColorAnimation { duration: app.motionMs(120) } }
        Behavior on scale {
            NumberAnimation { duration: app.motionMs(110); easing.type: Easing.OutCubic }
        }

        activeFocusOnTab: ch.tabbable

        Accessible.role: ch.checkbox ? Accessible.CheckBox
                                     : (ch.exclusive ? Accessible.RadioButton : Accessible.Button)
        Accessible.name: ch.label
        Accessible.description: ch.hint
        Accessible.focusable: true
        Accessible.focused: ch.activeFocus
        Accessible.checkable: ch.exclusive || ch.checkbox
        Accessible.checked: ch.selected
        Accessible.selected: ch.selected
        // The screen reader's own "press this" route, and the toggle path for
        // the radio case. Both land on the same signal as the mouse, so the
        // three routes cannot drift apart later.
        Accessible.onPressAction: ch.clicked()
        Accessible.onToggleAction: ch.clicked()

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                    || event.key === Qt.Key_Enter) {
                ch.clicked();
                event.accepted = true;
            }
        }

        FocusRing { ringRadius: ch.radius; on: ch.activeFocus }

        MouseArea {
            id: chMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            // Take focus on click so the ring follows the pointer user too.
            // Without this, clicking one card and then pressing Tab jumps back
            // to wherever focus was left, which feels like the window losing
            // its place.
            onClicked: {
                if (ch.tabbable)
                    ch.forceActiveFocus(Qt.MouseFocusReason);
                ch.clicked();
            }
        }
    }

    // A miniature desktop, painted live in the colours currently chosen. It is
    // what makes "Light" and "Dark" a picture instead of a word.
    //
    // Which is exactly why it is hidden from assistive technology: it is a
    // picture OF the choice, not a second choice. Announcing four anonymous
    // rectangles inside every card would bury the one label that matters.
    component MiniDesktop: Item {
        id: md
        property bool useDark: false
        property color accent: app.cAccent
        readonly property color mBg:    md.useDark ? "#0d1726" : "#dbe4f0"
        readonly property color mWin:   md.useDark ? "#16233a" : "#ffffff"
        readonly property color mEdge:  md.useDark ? "#27395a" : "#c6d2e4"
        readonly property color mPanel: md.useDark ? "#0a111c" : "#f2f6fc"

        Accessible.ignored: true

        Rectangle {
            anchors.fill: parent
            radius: app.px(7)
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

    // ============================================================ the window
    //
    // Header, body and footer are laid out here by hand rather than through
    // ApplicationWindow's header:/footer: properties, and the reason is the Tab
    // key. Those properties create their items outside the content item, and
    // Qt builds the focus chain from the order items appear in the tree — so
    // the wizard's real tab order came out FOOTER, then header, then the page.
    // The first Tab landed on "Back". A keyboard user met the escape hatches
    // before the question, on every screen, which is WCAG 2.4.3 Focus Order in
    // the plainest way it fails: the order no longer matches the reading order.
    // Declaring the three in visual order makes the focus chain correct by
    // construction instead of by a pile of KeyNavigation overrides that would
    // need re-checking every time a control is added.
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

    // A three-pixel gradient signature across the very top, Pro only. The
    // sleeker edition announces itself in decoration, never in text colour:
    // every contrast pair in this file was measured, and gloss that repaints
    // measured text is gloss that fails WCAG for whichever accent the owner
    // picks next. This strip carries no information a screen reader needs.
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: app.px(3)
        visible: app.edition === "pro"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0;  color: app.cAccent }
            GradientStop { position: 0.55; color: Qt.lighter(app.cAccent, 1.35) }
            GradientStop { position: 1.0;  color: "transparent" }
        }
        Accessible.ignored: true
    }

    // ================================================================= header
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: app.px(74)
        color: app.cPanel

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: app.cLine
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: app.px(22)
            anchors.rightMargin: app.px(18)
            spacing: app.px(14)

            Rectangle {
                Layout.preferredWidth: app.px(38)
                Layout.preferredHeight: app.px(38)
                Layout.alignment: Qt.AlignVCenter
                radius: app.px(11)
                color: app.cAccent
                Accessible.ignored: true       // brand mark, not information
                Text {
                    anchors.centerIn: parent
                    text: "D"
                    color: app.cOnAccent
                    font.pixelSize: app.px(22)
                    font.bold: true
                    // Without this Orca reads a lone letter "D" before the
                    // title on every single screen.
                    Accessible.ignored: true
                }
            }

            // minimumWidth 0 throughout, and it is load-bearing. Without it the
            // title block refuses to shrink below the width of its own
            // strapline, the RowLayout runs out of room, and "I'll do this
            // later" is pushed off the right-hand edge of the window — which
            // is where it went at 150% text on a small screen. A Layout will
            // happily overflow rather than squeeze an item that never said it
            // could be squeezed.
            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: app.windowTitle
                    color: app.cText
                    font.pixelSize: app.px(17)
                    font.bold: true
                    elide: Text.ElideRight
                    Accessible.role: Accessible.Heading
                    Accessible.name: app.windowTitle
                }
                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    // The strapline is the first thing to go when the window is
                    // cramped: it is reassurance, and the buttons beside it are
                    // function. Hiding it drops it from the accessibility tree
                    // too, which is fine here and only here — the welcome page
                    // says the same thing in its own words two lines later, so
                    // nobody loses the promise, only the repetition.
                    visible: app.width >= app.px(700)
                    text: app.t("Every step can be skipped, and you can change all of it later.")
                    color: app.cDim
                    font.pixelSize: app.px(12)
                    elide: Text.ElideRight
                    Accessible.role: Accessible.StaticText
                    // elide chops the VISIBLE text; the spoken text should be
                    // the whole sentence, not "Every step can be skipped, and…"
                    Accessible.name: app.t("Every step can be skipped, and you can change all of it later.")
                }
            }

            // The rail's job, in one line, for when there is no rail.
            //
            // The step list hides below 900px so it does not crush the page,
            // which is right — but it took the answer to "how much more of this
            // is there?" with it, and that is the single most reassuring thing
            // on screen for somebody who has just been talked into replacing
            // their operating system. A 1024x768 VM window lands at about
            // 860px, so the people most likely to lose it are exactly the
            // cautious ones evaluating Dagric in VirtualBox before they commit
            // a real machine.
            //
            // Visible on precisely the inverse of the rail's condition, so the
            // two can never both show and can never both be missing.
            Text {
                visible: app.width < app.px(900) && app.steps.length > 1
                Layout.alignment: Qt.AlignVCenter
                Layout.rightMargin: app.px(4)
                text: app.tf("Step %1 of %2", app.stepIndex + 1, app.steps.length)
                color: app.cDim
                font.pixelSize: app.px(12)
                Accessible.role: Accessible.StaticText
                Accessible.name: app.tf("Step %1 of %2", app.stepIndex + 1, app.steps.length)
                                 + ", " + app.stepTitle(app.steps[app.stepIndex])
            }

            Rectangle {
                visible: app.edition === "pro"
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: proLabel.implicitWidth + app.px(18)
                Layout.preferredHeight: app.px(24)
                radius: app.px(12)
                color: "transparent"
                border.width: 1
                border.color: app.cInkPanel
                Text {
                    id: proLabel
                    anchors.centerIn: parent
                    text: app.t("PRO EDITION")
                    // 2.56:1 as the raw accent on white. It is 10px text, so it
                    // is not "large" by any reading of 1.4.3 and needs the full
                    // 4.5:1. cInkPanel is the same hue, darkened until it does.
                    color: app.cInkPanel
                    font.pixelSize: app.px(10)
                    font.bold: true
                    Accessible.role: Accessible.StaticText
                    Accessible.name: app.t("Pro edition")
                }
            }

            Quiet {
                text: app.t("Undo my changes")
                visible: app.changed
                Layout.alignment: Qt.AlignVCenter
                Accessible.description: app.t("Put the colours, wallpaper, text size and taskbar back the way they were when setup opened")
                onClicked: app.undoAll()
            }

            Quiet {
                text: app.t("I'll do this later")
                Layout.alignment: Qt.AlignVCenter
                Accessible.description: app.t("Close setup. Anything already applied stays, and you can run this again from the Dagric Hub")
                onClicked: app.close()
            }
        }
    }

    // =================================================================== body
    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 0

        // --- the rail: where am I, and how much is left ----------------------
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: app.px(218)
            visible: app.width >= app.px(900)
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
                anchors.topMargin: app.px(24)
                anchors.leftMargin: app.px(18)
                anchors.rightMargin: app.px(18)
                spacing: app.px(4)

                Repeater {
                    model: app.steps
                    delegate: RowLayout {
                        id: railRow
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        spacing: app.px(11)

                        // The rail is a progress indicator, and the numbered
                        // circle plus the title only mean something together.
                        // Read as two separate items it comes out as "3" then
                        // "The taskbar", which is noise. One named item says
                        // the whole thing, and the two children go quiet.
                        Accessible.role: Accessible.StaticText
                        Accessible.name: app.tf("Step %1", railRow.index + 1) + ", "
                                         + app.stepTitle(railRow.modelData) + ", "
                                         + (railRow.index === app.stepIndex ? app.t("current step")
                                            : (railRow.index < app.stepIndex ? app.t("done")
                                               : app.t("not done yet")))

                        Rectangle {
                            Layout.preferredWidth: app.px(26)
                            Layout.preferredHeight: app.px(26)
                            radius: width / 2
                            color: railRow.index === app.stepIndex ? app.cAccent
                                 : (railRow.index < app.stepIndex ? app.cPanel2 : "transparent")
                            Behavior on color { ColorAnimation { duration: app.motionMs(150) } }
                            border.width: railRow.index > app.stepIndex ? 1 : 0
                            border.color: app.cEdge
                            Accessible.ignored: true
                            Text {
                                anchors.centerIn: parent
                                text: railRow.index < app.stepIndex ? "✓" : (railRow.index + 1)
                                color: railRow.index === app.stepIndex ? app.cOnAccent
                                     : (railRow.index < app.stepIndex ? app.cInkPanel2 : app.cDim)
                                font.pixelSize: app.px(13)
                                font.bold: true
                                Accessible.ignored: true
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            Layout.preferredHeight: app.px(40)
                            text: app.stepTitle(railRow.modelData)
                            color: railRow.index === app.stepIndex ? app.cText : app.cDim
                            font.pixelSize: app.px(14)
                            font.bold: railRow.index === app.stepIndex
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                            Accessible.ignored: true
                        }
                    }
                }
            }

            Text {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: app.px(18)
                text: app.live
                      ? app.t("Live trial — anything you set here lasts until you shut down.")
                      : app.editionName
                color: app.cDim
                font.pixelSize: app.px(11)
                wrapMode: Text.WordWrap
                Accessible.role: Accessible.StaticText
                Accessible.name: text
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
                width: parent.width - app.px(90)
                visible: app.loadError !== ""
                text: app.loadError
                color: app.cDim
                font.pixelSize: app.px(14)
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Accessible.role: Accessible.StaticText
                Accessible.name: app.loadError
            }

            // ------------------------------------------------------- welcome
            Page {
                label: app.t("Welcome")
                padWide: 40
                active: app.step === "welcome" && app.loadError === ""

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.preferredWidth: app.px(app.shortWin ? 64 : 88)
                    Layout.preferredHeight: app.px(app.shortWin ? 64 : 88)
                    radius: app.px(app.shortWin ? 18 : 24)
                    color: app.cAccent
                    // Pro's gloss: the brand tile catches the light. A
                    // top-lit vertical gradient on the tile only — the "D"
                    // keeps cOnAccent, whose contrast was chosen against the
                    // accent, and both gradient stops stay within a shade of
                    // that same accent.
                    gradient: app.edition === "pro" ? proTileGloss : null
                    Gradient {
                        id: proTileGloss
                        GradientStop { position: 0.0; color: Qt.lighter(app.cAccent, 1.18) }
                        GradientStop { position: 1.0; color: Qt.darker(app.cAccent, 1.10) }
                    }
                    Accessible.ignored: true
                    Text {
                        anchors.centerIn: parent
                        text: "D"
                        color: app.cOnAccent
                        font.pixelSize: app.px(app.shortWin ? 38 : 52)
                        font.bold: true
                        Accessible.ignored: true
                    }
                }

                Item { Layout.preferredHeight: app.px(app.shortWin ? 14 : 26) }

                Text {
                    Layout.fillWidth: true
                    text: app.tf("Welcome to %1.", app.editionName)
                    color: app.cText
                    font.pixelSize: app.px(34)
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.Heading
                    Accessible.name: text
                }

                Item { Layout.preferredHeight: app.px(app.shortWin ? 8 : 12) }

                Text {
                    Layout.fillWidth: true
                    Layout.maximumWidth: app.px(560)
                    // One whole sentence per language, not four fragments glued
                    // together: the Windows clause sits in the middle of the list
                    // in English and cannot be assumed to sit there anywhere else.
                    text: app.hasWindows
                          ? app.t("Let's make it yours. A few minutes now — the colours, the wallpaper, how big the text is, where the taskbar sits, and your files from Windows — and then it's out of your way.")
                          : app.t("Let's make it yours. A few minutes now — the colours, the wallpaper, how big the text is, where the taskbar sits — and then it's out of your way.")
                    color: app.cDim
                    font.pixelSize: app.px(16)
                    lineHeight: 1.35
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }

                Item { Layout.preferredHeight: app.px(app.shortWin ? 10 : 18) }

                Text {
                    Layout.fillWidth: true
                    Layout.maximumWidth: app.px(560)
                    text: app.live
                          ? app.t("You're running the live trial from the USB stick, so anything you set here lasts until you shut down. Install Dagric first if you want it to stick.")
                          : app.t("Every step can be skipped, and you can change all of it later.")
                    color: app.cDim
                    font.pixelSize: app.px(13)
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }

                Item { Layout.fillHeight: true }
            }

            // ---------------------------------------------------- appearance
            Page {
                label: app.t("How it looks")
                active: app.step === "appearance" && app.loadError === ""

                PageHead {
                    heading: app.t("Pick a look.")
                    sub: app.t("Click anything — the desktop behind this window changes as you go.")
                }

                // Flow, not RowLayout. At 150% text the two theme cards and the
                // colour swatches no longer fit side by side on a small screen,
                // and a RowLayout answers that by squashing everything until
                // the labels are unreadable. Wrapping is the honest answer.
                Flow {
                    Layout.fillWidth: true
                    spacing: app.px(14)

                    // Grouped so a screen reader announces "Theme, radio group"
                    // rather than dropping the user into two unexplained radio
                    // buttons floating in the page.
                    Row {
                        spacing: app.px(14)
                        Accessible.role: Accessible.Grouping
                        Accessible.name: app.t("Theme")

                        Choice {
                            id: lightChoice
                            width: app.px(178)
                            // The last 12px of the appearance page's overflow
                            // at 800x600, taken out of the picture rather than
                            // out of anything anybody reads. The label under it
                            // is untouched at every size; only the little
                            // painted desktop above it loses a few rows of
                            // pixels, and it is a hint at a theme, not a
                            // preview anybody inspects.
                            height: app.px(app.shortWin ? 96 : 108)
                            label: app.t("Light theme")
                            hint: app.t("A bright desktop. Shows a small picture of what it looks like.")
                            selected: app.mode === "light"
                            KeyNavigation.right: darkChoice
                            onClicked: app.pickMode("light")
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: app.px(10)
                                spacing: app.px(7)
                                MiniDesktop {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    useDark: false
                                }
                                Text {
                                    text: app.t("Light")
                                    color: app.cText
                                    font.pixelSize: app.px(13)
                                    font.bold: true
                                    Accessible.ignored: true
                                }
                            }
                        }

                        Choice {
                            id: darkChoice
                            width: app.px(178)
                            height: app.px(app.shortWin ? 96 : 108)   // matches Light, above
                            label: app.t("Dark theme")
                            hint: app.t("A dark desktop, easier on the eyes at night.")
                            selected: app.mode === "dark"
                            KeyNavigation.left: lightChoice
                            onClicked: app.pickMode("dark")
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: app.px(10)
                                spacing: app.px(7)
                                MiniDesktop {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    useDark: true
                                }
                                Text {
                                    text: app.t("Dark")
                                    color: app.cText
                                    font.pixelSize: app.px(13)
                                    font.bold: true
                                    Accessible.ignored: true
                                }
                            }
                        }
                    }

                    Column {
                        spacing: app.px(9)
                        visible: app.accents.length > 0
                        Accessible.role: Accessible.Grouping
                        Accessible.name: app.t("Highlight colour")

                        Text {
                            text: app.t("Highlight colour")
                            color: app.cDim
                            font.pixelSize: app.px(13)
                            Accessible.ignored: true      // said by the group
                        }

                        Flow {
                            width: app.px(200)
                            spacing: app.px(9)
                            Repeater {
                                id: accentRepeater
                                model: app.accents
                                delegate: Rectangle {
                                    id: swatch
                                    required property var modelData
                                    required property int index
                                    width: app.px(32)
                                    height: app.px(32)
                                    radius: width / 2
                                    color: swatch.modelData.hex
                                    border.width: app.accentId === swatch.modelData.id ? 3 : 1
                                    border.color: app.accentId === swatch.modelData.id
                                                  ? app.cText : app.cEdge

                                    // A colour with no name is unusable without
                                    // sight — and the tooltip that carried the
                                    // name was mouse-only, so it was unusable
                                    // without a mouse too.
                                    activeFocusOnTab: true
                                    Accessible.role: Accessible.RadioButton
                                    Accessible.name: swatch.modelData.name
                                    Accessible.description: app.t("Highlight colour")
                                    Accessible.focusable: true
                                    Accessible.focused: swatch.activeFocus
                                    Accessible.checkable: true
                                    Accessible.checked: app.accentId === swatch.modelData.id
                                    Accessible.selected: app.accentId === swatch.modelData.id
                                    Accessible.onPressAction: app.pickAccent(swatch.modelData)
                                    Accessible.onToggleAction: app.pickAccent(swatch.modelData)

                                    KeyNavigation.left: accentRepeater.itemAt(swatch.index - 1)
                                    KeyNavigation.right: accentRepeater.itemAt(swatch.index + 1)

                                    Keys.onPressed: function(event) {
                                        if (event.key === Qt.Key_Space
                                                || event.key === Qt.Key_Return
                                                || event.key === Qt.Key_Enter) {
                                            app.pickAccent(swatch.modelData);
                                            event.accepted = true;
                                        }
                                    }

                                    FocusRing { ringRadius: swatch.radius; on: swatch.activeFocus }

                                    // "Theme default" is not a colour of its own;
                                    // mark it so it does not read as plain blue.
                                    Text {
                                        anchors.centerIn: parent
                                        visible: swatch.modelData.id === "default"
                                        text: "✦"
                                        color: app.onColor(swatch.modelData.hex)
                                        font.pixelSize: app.px(14)
                                        Accessible.ignored: true
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        ToolTip.visible: containsMouse
                                        ToolTip.text: swatch.modelData.name
                                        onClicked: {
                                            swatch.forceActiveFocus(Qt.MouseFocusReason);
                                            app.pickAccent(swatch.modelData);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: app.px(2)
                    text: app.t("Wallpaper")
                    color: app.cDim
                    font.pixelSize: app.px(13)
                    visible: app.wallpapers.length > 0
                    Accessible.ignored: true          // said by the grid below
                }

                GridView {
                    id: wallGrid
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    // Preferred and minimum are deliberately THE SAME NUMBER,
                    // and that is most of why this page fits now.
                    //
                    // A page scrolls when its column's implicit height passes
                    // the viewport, and a Layout builds implicit height out of
                    // PREFERRED heights. Asking for 210 meant the page declared
                    // a need for 210px of gallery whether the window had it or
                    // not, and then scrolled the entire page — heading, theme
                    // cards and all — to satisfy the one element on it that has
                    // its own scrollbar and exists to be scrolled.
                    //
                    // So the gallery asks for the least it can live with, one
                    // full row of thumbnails, and takes back every spare pixel
                    // through fillHeight. On a roomy window that puts it back
                    // at 230-odd and nothing looks different; on a cramped one
                    // the page holds still and the gallery scrolls, which is
                    // the scrollbar the owner came expecting.
                    Layout.preferredHeight: app.px(130)
                    Layout.minimumHeight: app.px(130)
                    clip: true
                    visible: app.wallpapers.length > 0
                    model: app.wallpapers
                    cacheBuffer: 800

                    // ONE tab stop for the whole gallery, then arrow keys
                    // inside it. This is the shape every desktop uses for a
                    // grid of pictures, and the alternative — twenty tab stops
                    // between the theme cards and the Next button — is how you
                    // make a keyboard user give up on the third screen.
                    // GridView does the arrow handling itself once it has
                    // focus; what was missing was ever being able to reach it.
                    activeFocusOnTab: true
                    keyNavigationEnabled: true
                    keyNavigationWraps: false

                    Accessible.role: Accessible.List
                    Accessible.name: app.t("Wallpaper")
                    Accessible.description: app.t("Arrow keys to move between wallpapers, Space to apply one")

                    // Land on the wallpaper that is already set, so arrowing
                    // starts from where the desktop actually is.
                    Component.onCompleted: {
                        for (var i = 0; i < app.wallpapers.length; i++) {
                            if (app.wallpapers[i].id === app.wallId) {
                                wallGrid.currentIndex = i;
                                return;
                            }
                        }
                        wallGrid.currentIndex = 0;
                    }

                    property int columns: Math.max(2, Math.floor(width / app.px(190)))
                    cellWidth: Math.floor(width / columns)
                    cellHeight: Math.round((cellWidth - app.px(14)) * 0.5625) + app.px(30)

                    // Same rule as the page's own bar: a replaced contentItem
                    // has lost the style's fade, so it must be switched off
                    // outright when there is nothing under the fold. Five
                    // wallpapers on one row and a permanent bar beside them
                    // reads as "there are more" — and there are not.
                    ScrollBar.vertical: ScrollBar {
                        policy: wallGrid.contentHeight > wallGrid.height
                                ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                        contentItem: Rectangle {
                            implicitWidth: app.px(6)
                            radius: app.px(3)
                            color: app.cEdge
                        }
                    }

                    delegate: Item {
                        id: wcell
                        required property var modelData
                        required property int index
                        width: GridView.view ? GridView.view.cellWidth : app.px(180)
                        height: GridView.view ? GridView.view.cellHeight : app.px(120)

                        readonly property bool chosen: app.wallId === wcell.modelData.id

                        // Roving focus: the CURRENT cell is the one that holds
                        // real keyboard focus, so Orca announces the wallpaper
                        // the arrow keys just landed on instead of announcing
                        // "list" once and then going silent.
                        focus: wcell.GridView.isCurrentItem

                        Accessible.role: Accessible.RadioButton
                        Accessible.name: wcell.modelData.name
                        Accessible.description: app.tf("Wallpaper %1 of %2",
                                                       wcell.index + 1,
                                                       app.wallpapers.length)
                        Accessible.focusable: true
                        Accessible.focused: wcell.activeFocus
                        Accessible.checkable: true
                        Accessible.checked: wcell.chosen
                        Accessible.selected: wcell.chosen
                        Accessible.onPressAction: app.pickWall(wcell.modelData)
                        Accessible.onToggleAction: app.pickWall(wcell.modelData)

                        // Arrow keys are deliberately NOT handled here: leaving
                        // them unaccepted lets them bubble up to the GridView,
                        // which is what moves the current index.
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Space
                                    || event.key === Qt.Key_Return
                                    || event.key === Qt.Key_Enter) {
                                app.pickWall(wcell.modelData);
                                event.accepted = true;
                            }
                        }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: app.px(6)
                            radius: app.px(9)
                            color: "transparent"
                            border.width: wcell.chosen ? 2 : 1
                            border.color: wcell.chosen
                                          ? app.cSelect
                                          : (wmouse.containsMouse ? app.cDim : app.cEdge)

                            // The ring lives on the frame, over the photograph.
                            // This is the case the two-tone ring was built for.
                            FocusRing { ringRadius: app.px(9); on: wcell.activeFocus }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: app.px(4)
                                spacing: app.px(3)

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true

                                    // Underneath always: a flat tile, so a
                                    // wallpaper that fails to decode shows as a
                                    // blank card and never a broken-image icon.
                                    Rectangle {
                                        anchors.fill: parent
                                        radius: app.px(6)
                                        color: app.cPanel2
                                    }

                                    Image {
                                        anchors.fill: parent
                                        source: wcell.modelData.thumb
                                        fillMode: Image.PreserveAspectCrop
                                        asynchronous: true
                                        visible: status === Image.Ready
                                        // The tile already carries the name.
                                        // Announcing the picture as well gives
                                        // every wallpaper two entries in the
                                        // tree, one of them nameless.
                                        Accessible.ignored: true
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
                                    color: wcell.chosen ? app.cText : app.cDim
                                    font.pixelSize: app.px(11)
                                    elide: Text.ElideRight
                                    horizontalAlignment: Text.AlignHCenter
                                    Accessible.ignored: true
                                }
                            }

                            MouseArea {
                                id: wmouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    wallGrid.currentIndex = wcell.index;
                                    wallGrid.forceActiveFocus(Qt.MouseFocusReason);
                                    app.pickWall(wcell.modelData);
                                }
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: app.t("Want your own picture? Right-click the desktop and choose Configure Desktop.")
                    color: app.cDim
                    font.pixelSize: app.px(11)
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }

            // ------------------------------------------------------- display
            Page {
                label: app.t("Text size")
                padWide: 40
                active: app.step === "display" && app.loadError === ""

                PageHead {
                    heading: app.t("Is the text the right size?")
                    sub: app.hasDisplayTool
                         ? app.t("Dagric guessed from your screen. Pick another size if it guessed wrong.")
                         : (app.scaleMode === "x11"
                            ? app.t("Dagric guessed from your screen. A change here takes effect the next time you sign in.")
                            : app.t("Dagric guessed from your screen. Pick another size and it changes right away."))
                }

                // The dedicated tool owns this properly when it is installed —
                // shipping a second, disagreeing text-size control would just
                // give support two answers to the same question.
                //
                // THE LABEL NAMES THE ACTION, NOT A DESTINATION, and it used to
                // do neither correctly. It read "Open Display Settings", which
                // in KDE means one specific thing: System Settings ▸ Display &
                // Monitor. The button does not open that. It opens a small
                // Dagric window — and the footer four lines below this one
                // names the real System Settings page, so the page carried two
                // similar phrases pointing at two different places, with the
                // wrong one on the button. "Choose a text size" cannot be
                // misread, and stays true whichever window the helper draws.
                RowLayout {
                    Layout.fillWidth: true
                    spacing: app.px(14)
                    visible: app.hasDisplayTool

                    Primary {
                        text: app.t("Choose a text size")
                        Accessible.description: app.t("Opens a list of text sizes in a separate window. A new size is tried for twenty seconds and put back on its own unless you keep it.")
                        onClicked: { app.markVisited("display"); app.run("display"); }
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: app.px(14)
                    visible: !app.hasDisplayTool

                    Accessible.role: Accessible.Grouping
                    Accessible.name: app.t("Text size")

                    Repeater {
                        id: sizeRepeater
                        // The model holds the ENGLISH names; every place that
                        // shows one puts it through app.t() first. Storing the
                        // translation here instead would make the model depend on
                        // the catalogue having loaded, and these three cards are
                        // built before it has.
                        model: [
                            { v: 100, name: "Normal",  note: "Standard size" },
                            { v: 125, name: "Bigger",  note: "Easier to read" },
                            { v: 150, name: "Biggest", note: "Large text" }
                        ]
                        delegate: Choice {
                            id: sizeCard
                            required property var modelData
                            required property int index
                            width: app.px(176)
                            height: app.px(132)
                            label: app.tf("%1, %2 percent",
                                          app.t(sizeCard.modelData.name), sizeCard.modelData.v)
                            hint: app.t(sizeCard.modelData.note)
                            selected: app.scale === sizeCard.modelData.v
                            KeyNavigation.left: sizeRepeater.itemAt(sizeCard.index - 1)
                            KeyNavigation.right: sizeRepeater.itemAt(sizeCard.index + 1)
                            onClicked: app.pickScale(sizeCard.modelData.v)
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: app.px(14)
                                spacing: app.px(4)
                                Text {
                                    text: "Aa"
                                    color: app.cText
                                    // Draw the sizes at their real ratio, so the
                                    // card shows the answer instead of naming it.
                                    font.pixelSize: app.px(Math.round(22 * sizeCard.modelData.v / 100))
                                    font.bold: true
                                    Accessible.ignored: true
                                }
                                Item { Layout.fillHeight: true }
                                Text {
                                    text: app.t(sizeCard.modelData.name) + "  " + sizeCard.modelData.v + "%"
                                    color: app.cText
                                    font.pixelSize: app.px(14)
                                    font.bold: true
                                    Accessible.ignored: true
                                }
                                Text {
                                    text: app.t(sizeCard.modelData.note)
                                    color: app.cDim
                                    font.pixelSize: app.px(12)
                                    Accessible.ignored: true
                                }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: app.t("You can change this again in System Settings ▸ Display & Monitor.")
                    color: app.cDim
                    font.pixelSize: app.px(12)
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }

            // ------------------------------------------------------- taskbar
            Page {
                label: app.t("The taskbar")
                active: app.step === "taskbar" && app.loadError === ""

                PageHead {
                    heading: app.t("Where should the taskbar go?")
                    sub: app.t("Click one to try it. Your open windows and apps stay exactly where they are.")
                }

                GridView {
                    id: layoutGrid
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    // Same rule as the wallpaper gallery: ask for one row, take
                    // the slack through fillHeight. A preferred height larger
                    // than the minimum is a page-level scrollbar waiting for a
                    // short enough window.
                    Layout.preferredHeight: app.px(160)
                    Layout.minimumHeight: app.px(160)
                    clip: true
                    model: app.layouts
                    cacheBuffer: 800

                    activeFocusOnTab: true
                    keyNavigationEnabled: true
                    keyNavigationWraps: false

                    Accessible.role: Accessible.List
                    Accessible.name: app.t("Taskbar layout")
                    Accessible.description: app.t("Arrow keys to move between layouts, Space to try one")

                    Component.onCompleted: layoutGrid.currentIndex = 0

                    property int columns: Math.max(2, Math.floor(width / app.px(250)))
                    cellWidth: Math.floor(width / columns)
                    // Room for the picture, the name, and TWO lines of the
                    // description. One line elided "a taskbar at the bottom,
                    // familiar and c…" — which cuts the sentence exactly where
                    // it was about to say the reassuring part.
                    cellHeight: Math.round((cellWidth - app.px(24)) * 0.5625) + app.px(78)

                    ScrollBar.vertical: ScrollBar {
                        policy: layoutGrid.contentHeight > layoutGrid.height
                                ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                        contentItem: Rectangle {
                            implicitWidth: app.px(6)
                            radius: app.px(3)
                            color: app.cEdge
                        }
                    }

                    delegate: Item {
                        id: lcell
                        required property var modelData
                        required property int index
                        width: GridView.view ? GridView.view.cellWidth : app.px(240)
                        height: GridView.view ? GridView.view.cellHeight : app.px(180)

                        focus: lcell.GridView.isCurrentItem

                        Choice {
                            anchors.fill: parent
                            anchors.margins: app.px(7)
                            // The grid owns the tab stop; this card is reached
                            // with the arrow keys, like every other picture
                            // grid on the desktop.
                            tabbable: false
                            focus: true
                            label: lcell.modelData.name
                            hint: lcell.modelData.desc
                            selected: app.layoutId === lcell.modelData.id
                            onClicked: {
                                layoutGrid.currentIndex = lcell.index;
                                layoutGrid.forceActiveFocus(Qt.MouseFocusReason);
                                app.pickLayout(lcell.modelData);
                            }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: app.px(9)
                                spacing: app.px(7)

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    Rectangle {
                                        anchors.fill: parent
                                        radius: app.px(6)
                                        color: app.cPanel2
                                    }
                                    Image {
                                        anchors.fill: parent
                                        source: lcell.modelData.thumb
                                        fillMode: Image.PreserveAspectCrop
                                        asynchronous: true
                                        visible: status === Image.Ready
                                        sourceSize.width: 420
                                        Accessible.ignored: true
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: lcell.modelData.name
                                    color: app.cText
                                    font.pixelSize: app.px(13)
                                    font.bold: true
                                    elide: Text.ElideRight
                                    Accessible.ignored: true
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: lcell.modelData.desc
                                    color: app.cDim
                                    font.pixelSize: app.px(11)
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                    Accessible.ignored: true
                                }
                            }
                        }
                    }
                }
            }

            // --------------------------------------------------------- files
            Page {
                label: app.t("Your files")
                padWide: 40
                active: app.step === "files" && app.loadError === ""

                PageHead {
                    heading: app.t("Bring your files across.")
                    sub: app.t("There's a Windows drive in this PC. Dagric can copy your Documents, Pictures, Music, Videos, Downloads and browser bookmarks over.")
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.maximumWidth: app.px(640)
                    Layout.preferredHeight: contentCol.implicitHeight + app.px(34)
                    radius: app.px(12)
                    color: app.cPanel
                    border.width: 1
                    border.color: app.cLine

                    // The promise this panel makes is the single most reassuring
                    // sentence in the wizard for somebody who is frightened of
                    // losing their photos. Grouped so it is read as one thing.
                    Accessible.role: Accessible.Grouping
                    Accessible.name: app.t("Windows is only ever read.")

                    ColumnLayout {
                        id: contentCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: app.px(17)
                        spacing: app.px(8)
                        Text {
                            Layout.fillWidth: true
                            text: app.t("Windows is only ever READ.")
                            color: app.cText
                            font.pixelSize: app.px(14)
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Accessible.role: Accessible.StaticText
                            Accessible.name: app.t("Windows is only ever read.")
                        }
                        Text {
                            Layout.fillWidth: true
                            text: app.t("Nothing on the Windows drive is moved, changed or deleted, and files already here are never overwritten. If you change your mind about Dagric, Windows is exactly as you left it.")
                            color: app.cDim
                            font.pixelSize: app.px(13)
                            wrapMode: Text.WordWrap
                            Accessible.role: Accessible.StaticText
                            Accessible.name: text
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: app.px(12)
                    Primary {
                        text: app.t("Bring my files over")
                        Accessible.description: app.t("Opens the migration tool in its own window. Nothing on the Windows drive is changed.")
                        onClicked: { app.markVisited("files"); app.run("migrate"); }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: app.t("This opens in its own window — carry on here while it works.")
                        color: app.cDim
                        font.pixelSize: app.px(12)
                        wrapMode: Text.WordWrap
                        Accessible.role: Accessible.StaticText
                        Accessible.name: text
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: app.t("Not now? It's in the Dagric Hub under \"Migrate from Windows\", any time.")
                    color: app.cDim
                    font.pixelSize: app.px(12)
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }

            // ----------------------------------------------------- downloads
            //
            // The one-click apps, offered where a Windows switcher expects
            // them: during setup. Every card is a CONSENT, not an install —
            // ticking one queues its name, and the queue runs in a terminal
            // the owner can read only after Finish, because this window is
            // fullscreen and anything launched now would open behind it.
            // The card model reuses the finish page's exact { act, title,
            // body } shape on purpose: tools/i18n-wizard.py extracts card
            // strings by that shape, and a new shape would ship untranslated
            // cards with the checker saying nothing.
            Page {
                label: app.t("Add your apps")
                active: app.step === "downloads" && app.loadError === ""

                PageHead {
                    heading: app.t("Add your apps")
                    sub: app.t("Choose what you want. Each installer opens after Finish and asks before making changes. Some choices are third-party or proprietary; none is required.")
                }

                Flow {
                    id: dlFlow
                    Layout.fillWidth: true
                    spacing: app.px(10)
                    // Same clamp idea as the finish cards: never let a card
                    // grow past a comfortable reading width, never shrink one
                    // below its label.
                    readonly property real cardW: Math.max(app.px(170), Math.min(app.px(210), (width - spacing * 2) / 3))

                    Repeater {
                        id: dlRepeater
                        model: [
                            { act: "steam", title: "Steam",
                              body: "Optional proprietary Valve client; vendor terms apply." },
                            { act: "heroic", title: "Heroic",
                              body: "Independent launcher for Epic Games Store, GOG and Amazon Games." },
                            { act: "bottles", title: "Bottles",
                              body: "Run Windows programs in separate Wine environments." },
                            { act: "onlyoffice", title: "ONLYOFFICE",
                              body: "An office suite that looks like the one at work." },
                            { act: "joplin", title: "Joplin",
                              body: "Private notes that sync anywhere." },
                            { act: "localsend", title: "LocalSend",
                              body: "Share files between your devices, no cloud." },
                            { act: "cryptomator", title: "Cryptomator",
                              body: "Encrypt what you keep in the cloud." },
                            { act: "upscayl", title: "Upscayl",
                              body: "Sharpen old photos with AI." },
                            { act: "ai", title: "Ollama",
                              body: "A local AI that never leaves this machine." }
                        ]
                        delegate: Choice {
                            id: dlCard
                            required property var modelData
                            required property int index
                            width: dlFlow.cardW
                            height: app.px(108)
                            exclusive: false
                            checkbox: true
                            selected: app.appsPicked.indexOf(dlCard.modelData.act) >= 0
                            label: app.t(dlCard.modelData.title)
                            hint: app.t(dlCard.modelData.body)
                                  + (dlCard.selected
                                     ? " " + app.t("Selected — starts when you press Finish.")
                                     : "")
                            KeyNavigation.left: dlRepeater.itemAt(dlCard.index - 1)
                            KeyNavigation.right: dlRepeater.itemAt(dlCard.index + 1)
                            onClicked: app.toggleApp(dlCard.modelData.act)
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: app.px(14)
                                spacing: app.px(6)
                                Text {
                                    Layout.fillWidth: true
                                    text: app.t(dlCard.modelData.title)
                                    color: app.cText
                                    font.pixelSize: app.px(14)
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                    Accessible.ignored: true
                                }
                                Text {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: app.t(dlCard.modelData.body)
                                    color: app.cDim
                                    font.pixelSize: app.px(11)
                                    wrapMode: Text.WordWrap
                                    verticalAlignment: Text.AlignTop
                                    Accessible.ignored: true
                                }
                                Text {
                                    text: dlCard.selected ? "✓ " + app.t("Selected") : ""
                                    color: app.cInkPanel
                                    font.pixelSize: app.px(11)
                                    font.bold: true
                                    Accessible.ignored: true
                                }
                            }
                        }
                    }
                }

                // The free→Pro pipeline, in the wizard itself. Installed free
                // machines only: on the live stick the upgrade tool refuses to
                // run (RAM-only, money for nothing), and on Pro there is
                // nothing to sell.
                Choice {
                    Layout.fillWidth: true
                    Layout.preferredHeight: app.px(84)
                    visible: app.edition !== "pro" && !app.live
                    exclusive: false
                    checkbox: true
                    selected: app.proPicked
                    label: app.t("Already bought Pro?")
                    hint: app.t("Paste the code from your receipt and this machine becomes Pro — your files and settings stay.")
                          + (app.proPicked
                             ? " " + app.t("Selected — starts when you press Finish.")
                             : "")
                    onClicked: app.toggleProUpgrade()
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: app.px(14)
                        spacing: app.px(12)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: app.px(4)
                            Text {
                                Layout.fillWidth: true
                                text: app.t("Already bought Pro?")
                                color: app.cText
                                font.pixelSize: app.px(14)
                                font.bold: true
                                wrapMode: Text.WordWrap
                                Accessible.ignored: true
                            }
                            Text {
                                Layout.fillWidth: true
                                text: app.t("Paste the code from your receipt and this machine becomes Pro — your files and settings stay.")
                                color: app.cDim
                                font.pixelSize: app.px(11)
                                wrapMode: Text.WordWrap
                                Accessible.ignored: true
                            }
                        }
                        Text {
                            text: app.proPicked ? "✓ " + app.t("Selected") : ""
                            color: app.cInkPanel
                            font.pixelSize: app.px(11)
                            font.bold: true
                            Accessible.ignored: true
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: app.live
                          ? app.t("This is the live trial: anything you add now lives in memory, disappears at shutdown, and can make a machine with little RAM unstable. Install Dagric first to keep it.")
                          : app.t("Nothing here is a subscription, and everything can be removed later from the Software Store.")
                    color: app.cDim
                    font.pixelSize: app.px(12)
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }

            // -------------------------------------------------------- finish
            Page {
                label: app.t("You're ready")
                // No padWide bump here, unlike the other prose pages. This one
                // is four cards rather than three paragraphs, and the 40 it
                // used to carry was what put it four pixels past the bottom at
                // 1060x720 — a scrollbar on the last screen of the wizard, at
                // the window's own default size, to buy six pixels of margin
                // around a grid that already has margins of its own.
                active: app.step === "finish" && app.loadError === ""

                PageHead {
                    heading: app.tf("That's it — %1 is yours.", app.editionName)
                    sub: app.t("Four places worth knowing about. Everything else you can find by pressing the launcher and typing.")
                }

                Flow {
                    id: finishFlow
                    Layout.fillWidth: true
                    spacing: app.px(14)

                    // Four across whenever four across will fit — worked out
                    // from the width there actually is, not from a guess about
                    // which windows are small.
                    //
                    // A flat 196 wanted 826px for the row. The page has between
                    // 690 and 780, so the four wrapped two-and-two on EVERY
                    // window this wizard opens on, and the second row is what
                    // pushed this page off the bottom. A flat "narrower when
                    // the window is short" fixed the sizes we had measured and
                    // broke again the moment the desktop font grew: the cards
                    // scale with the font, the window does not, and at a 1.09
                    // text scale 4x172 no longer fit in a page that was still
                    // 984px wide. Dividing the room by four cannot drift like
                    // that. The clamps are the two ends of the useful range —
                    // never wider than the original 196, never so narrow the
                    // body text turns into a column of two-word lines, and if
                    // even 146 will not fit four times the Flow wraps, which is
                    // the correct answer at that size rather than a failure.
                    readonly property real cardW:
                        Math.max(app.px(146),
                                 Math.min(app.px(196),
                                          Math.floor((finishFlow.width - 3 * finishFlow.spacing) / 4)))

                    // "guide" and "manual" are two different documents and the
                    // cards have to say so, because an owner who opens the
                    // wrong one and finds nothing about their printer concludes
                    // Dagric has no help. Guide = your first week. Manual = a
                    // page per application, offline, searchable by the Windows
                    // name you already know.
                    Repeater {
                        id: finishRepeater
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
                            id: linkCard
                            required property var modelData
                            required property int index
                            width: finishFlow.cardW
                            // 162 is measured, not chosen. The tallest of the
                            // four (Dagric Hub and App Manual tie) asks for
                            // 136px of content at a 158px card width and about
                            // 152 at the narrowest width the clamp above will
                            // hand out — title, the body wrapped as far as it
                            // wraps, and the "Open →" line, which is the part
                            // that used to fall off the bottom. 170 was 34px of
                            // air, and 34px x 2 rows is a scrollbar.
                            height: app.px(162)
                            // These four open something. They are not a choice
                            // between alternatives, so they are buttons and not
                            // radio buttons — a screen reader that says "radio
                            // button, 1 of 4" here is describing a decision the
                            // owner is not being asked to make.
                            exclusive: false
                            label: app.tf("Open %1", app.t(linkCard.modelData.title))
                            hint: app.t(linkCard.modelData.body)
                            KeyNavigation.left: finishRepeater.itemAt(linkCard.index - 1)
                            KeyNavigation.right: finishRepeater.itemAt(linkCard.index + 1)
                            onClicked: app.run(linkCard.modelData.act)
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: app.px(16)
                                spacing: app.px(8)
                                Text {
                                    Layout.fillWidth: true
                                    text: app.t(linkCard.modelData.title)
                                    color: app.cText
                                    font.pixelSize: app.px(15)
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                    Accessible.ignored: true
                                }
                                Text {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: app.t(linkCard.modelData.body)
                                    color: app.cDim
                                    font.pixelSize: app.px(12)
                                    wrapMode: Text.WordWrap
                                    verticalAlignment: Text.AlignTop
                                    Accessible.ignored: true
                                }
                                Text {
                                    text: app.t("Open") + "  →"
                                    // Was the raw accent: 2.56:1 on a white
                                    // card, and this is 12px text.
                                    color: app.cInkPanel
                                    font.pixelSize: app.px(12)
                                    font.bold: true
                                    Accessible.ignored: true
                                }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: app.live
                          ? app.t("This is the live trial. To keep any of it, run Install Dagric OS from the desktop.")
                          : app.t("Want to run through this again? It's called \"Set Up Dagric\" in your apps list.")
                    color: app.cDim
                    font.pixelSize: app.px(13)
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }
        }
    }

    // ================================================================= footer
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: app.px(74)
        color: app.cPanel

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: app.cLine
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: app.px(22)
            anchors.rightMargin: app.px(22)
            spacing: app.px(12)

            Ghost {
                text: app.t("Back")
                visible: app.stepIndex > 0
                onClicked: app.goBack()
            }

            Item { Layout.fillWidth: true }

            // Only offered while this step is still unanswered. Once something
            // here has been clicked there is nothing left to skip, and two
            // buttons that do the same thing is a puzzle, not a choice.
            Quiet {
                text: app.t("Skip this step")
                visible: app.step !== "welcome" && app.step !== "finish"
                         && !app.isTouched(app.step)
                Accessible.description: app.t("Leave this setting alone and go to the next step")
                onClicked: app.goNext()
            }

            Primary {
                text: app.step === "finish" ? app.t("Finish")
                    : (app.step === "welcome" ? app.t("Let's go") : app.t("Next"))
                onClicked: app.goNext()
            }
        }
    }

    }   // end of the header / body / footer column
}
