// SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Dagric OS — the slides shown while the installer copies the system across.
//
// ---------------------------------------------------------------- TRANSLATION
//
// These three slides are the only words in the installer that are ours; every
// other sentence Calamares puts on screen it translates itself. Until this
// comment existed they were bare English literals, so a French buyer picked
// French on the welcome page and then watched an English slideshow for the ten
// minutes the copy takes.
//
// They are qsTr() here rather than gettext, which is the opposite of the
// decision made for the first-run wizard (see the long note in
// usr/bin/dagric-firstrun). The reason the wizard's argument does not apply:
// that wizard is launched by our own shell script, which can read the gettext
// catalogue and hand the strings in as data. NOTHING OF OURS LAUNCHES THIS
// FILE. Calamares loads it itself, into its own QML engine, so the only way a
// string in here can be translated is the one Calamares implements.
//
// That mechanism, read out of the Calamares 3.3 source rather than assumed:
//
//   * Branding.cpp builds a prefix of "<branding dir>/lang/calamares-<component>"
//     and BrandingLoader::tryLoad() in utils/Retranslator.cpp appends
//     "_<locale>", so the catalogues are lang/calamares-dagric_<locale>.qm.
//     Component name comes from branding.desc; ours is "dagric".
//   * Slideshow.cpp line 57 wraps the QML engine in CALAMARES_RETRANSLATE and
//     calls engine()->retranslate(), which is what makes this work at all with
//     slideshowAPI 2: API 2 loads this file at STARTUP, before the owner has
//     chosen a language, and the retranslate() call is what re-evaluates these
//     bindings when they pick one on the welcome page.
//   * A missing catalogue is not a failure — qsTr() returns the source string,
//     which is the English below. That is also what the _en catalogue is for.
//
// Calamares' own default branding does exactly this: /usr/share/calamares/
// branding/default/ ships lang/calamares-default_{ar,en,eo,fr,nl}.qm beside a
// show.qml that uses qsTr(). Checked inside the built ISO, not in a document.
//
// The .ts sources sit in lang/ next to the compiled .qm, and are committed for
// the same reason po/ commits .mo beside .po: a catalogue nobody can read is a
// catalogue nobody can correct. To change a slide, edit the English here and
// then, from this directory:
//
//     lupdate show.qml -ts lang/calamares-dagric_de.ts \
//                          lang/calamares-dagric_es.ts ...
//     lrelease lang/*.ts
//
// (/usr/lib/qt6/bin, package qt6-l10n-tools, build host only — only the .qm
// ships.) An unfinished message is not a build error; lrelease drops it and
// that slide quietly reverts to English, so check lrelease's counts.
//
// Product names are NOT translated, matching the guard in tools/i18n-review.py:
// "Dagric", "Dagric OS" and "Discover" stay as they are in every language, and
// so do the two Old English roots "dagr" and "ric" — only their glosses move.

import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    Timer {
        interval: 12000
        running: presentation.activatedInSlideshow
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        anchors.fill: parent
        Rectangle { anchors.fill: parent; color: "#0b1118" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.7
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "#e6edf3"; font.pixelSize: 22
            text: qsTr("Welcome to Dagric OS.\n\nDagric — from dagr (day) and ric (ruler).\nYour computer, your day, your rule.")
        }
    }

    Slide {
        anchors.fill: parent
        Rectangle { anchors.fill: parent; color: "#0b1118" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.7
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "#e6edf3"; font.pixelSize: 22
            text: qsTr("No telemetry. No ads. No accounts.\n\nSecurity updates install silently in the background,\nand the machine reboots only when you say so.")
        }
    }

    Slide {
        anchors.fill: parent
        Rectangle { anchors.fill: parent; color: "#0b1118" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.7
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "#e6edf3"; font.pixelSize: 22
            text: qsTr("Need more software?\n\nOpen Discover to install thousands of apps —\nchosen by you, sandboxed, removable.")
        }
    }
}
