// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Window
import QtTest

TestCase {
    id: tests
    name: "DagricFirstRun"
    when: windowShown
    property var wizard

    function init() {
        var c = Qt.createComponent("../../config/includes.chroot/usr/share/dagric/firstrun/main.qml");
        compare(c.status, Component.Ready, c.errorString());
        wizard = c.createObject(null, {visibility: Window.Windowed, width: 800, height: 600});
        verify(wizard !== null);
        wizard.loadError = "";
        wizard.loaded = true;
        wizard.mode = "dark";
        wizard.scaleMode = "wayland";
        wizard.scaleReady = true;
        wizard.allowedScales = [100, 125, 150];
        wizard.layouts = [{id:"classic", name:"Familiar", desc:"Bottom panel", thumb:""},
                          {id:"eleven", name:"Modern", desc:"Centered apps", thumb:""}];
        wizard.buildSteps();
        wait(250);
    }
    function cleanup() { wizard.destroy(); }

    function test_trial_blocks_navigation() {
        wizard.stepIndex = 1;
        wizard.scaleTrial = true;
        wizard.goNext();
        compare(wizard.stepIndex, 1);
        wizard.goBack();
        compare(wizard.stepIndex, 1);
        wizard.scaleTrial = false;
        wizard.goNext();
        compare(wizard.stepIndex, 2);
    }

    function test_progress_and_reduced_motion() {
        wizard.reducedMotion = true;
        compare(wizard.motionMs(200), 0);
        var progress = findChild(wizard.contentItem, "setupProgress");
        verify(progress !== null);
        wizard.stepIndex = 0;
        wait(10);
        var firstWidth = progress.width;
        verify(firstWidth > 0);
        wizard.stepIndex = wizard.steps.length - 1;
        wait(10);
        verify(progress.width > firstWidth);
        compare(progress.width, progress.parent.width);
        wizard.reducedMotion = false;
        compare(wizard.motionMs(200), 200);
    }

    function test_decorative_motion_is_finite_and_optional() {
        var c = Qt.createComponent("../../config/includes.chroot/usr/share/dagric/design/Aperture.qml");
        compare(c.status, Component.Ready, c.errorString());
        var art = c.createObject(wizard.contentItem, {width:400,height:400,animate:false});
        verify(art !== null);
        compare(art.reveal, 1);
        art.animate = true;
        art.enter();
        wait(60);
        verify(art.moving);
        var start = grabImage(art);
        wait(1000);
        verify(!art.moving);
        compare(art.reveal, 1);
        verify(!grabImage(art).equals(start));
        art.enter();
        art.reducedMotion = true;
        verify(!art.moving);
        compare(art.reveal, 1);
        var still = grabImage(art);
        wait(150);
        verify(grabImage(art).equals(still));
        art.destroy();
    }

    function test_layout_preview_does_not_resize_window() {
        var w = wizard.width, h = wizard.height, x = wizard.x, y = wizard.y;
        wizard.pickLayout(wizard.layouts[1]);
        wait(250);
        compare(wizard.layoutId, "eleven");
        compare(wizard.width, w); compare(wizard.height, h);
        compare(wizard.x, x); compare(wizard.y, y);
        wizard.undoAll();
        compare(wizard.layoutId, "");
    }

    function test_size_waits_for_backend() {
        wizard.scale = 100;
        wizard.pickScale(125);
        compare(wizard.scale, 100);
        verify(wizard.scaleBusy);
        verify(!wizard.isTouched("display"));
    }

    function test_x11_size_waits_for_save_and_preview_is_explicit() {
        wizard.scaleMode = "x11";
        wizard.stepIndex = wizard.steps.indexOf("display");
        wizard.scale = 100;
        wizard.pickScale(125);
        verify(wizard.scaleBusy);
        compare(wizard.scale, 100);
        wizard.scaleBusy = false;
        wizard.scale = 125; // backend acknowledgement
        wait(250);
        var selected = findChild(wizard.contentItem, "textSize125");
        verify(selected.selected);
        verify(findChild(wizard.contentItem, "textSizeSelection").text.indexOf("125%") >= 0);
        var sample = findChild(wizard.contentItem, "textSizeSample");
        compare(sample.font.pixelSize, wizard.px(20));
        var imagePath = decodeURIComponent(Qt.resolvedUrl("../../out/text-size-selected-preview.png").toString().replace("file://", ""));
        grabImage(wizard.contentItem).save(imagePath);
    }

    function test_install_available_only_on_live_media_data() {
        return [{tag:"free",edition:"free"}, {tag:"pro",edition:"pro"}];
    }
    function test_install_available_only_on_live_media(data) {
        wizard.edition = data.edition;
        wizard.editionName = data.edition === "pro" ? "Dagric OS Pro" : "Dagric OS";
        wizard.live = true; wizard.canInstall = true;
        var install = findChild(wizard.contentItem, "setupInstall");
        wait(20); verify(install.visible);
        var p = install.mapToItem(wizard.contentItem, 0, 0);
        verify(p.y >= 0 && p.y + install.height <= wizard.height - wizard.px(74));
        var path = decodeURIComponent(Qt.resolvedUrl("../../out/unified-setup-"+data.edition+".png").toString().replace("file://", ""));
        grabImage(wizard.contentItem).save(path);
        wizard.live = false;
        wait(20); verify(!install.visible);
        wizard.install();
        verify(!wizard.finished);
    }

    function test_waiting_for_display_does_not_block_navigation() {
        wizard.width = 800; wizard.height = 600;
        wizard.stepIndex = wizard.steps.indexOf("display");
        wizard.scaleMode = "wayland";
        wizard.scaleReady = false;
        wait(30);
        var notice = findChild(wizard.contentItem, "textSizeWaiting");
        verify(notice.visible);
        verify(notice.text.indexOf("Waiting for display setup") >= 0);
        var next = findChild(wizard.contentItem, "setupNext");
        verify(next.enabled);
        var p = next.mapToItem(wizard.contentItem, 0, 0);
        verify(p.y + next.height <= wizard.height + 1);
        wizard.scaleReady = true;
        wait(20);
        verify(!notice.visible);
    }

    function test_boot_art_moves_without_moving_text_and_stops() {
        var c = Qt.createComponent("../../config/includes.chroot/usr/share/plasma/look-and-feel/org.dagric.splash/contents/splash/Splash.qml");
        var splash = c.createObject(wizard.contentItem, {width:800,height:600,stage:1});
        verify(splash !== null);
        splash.reducedMotion = false;
        var art = findChild(splash, "startupAperture");
        var word = findChild(splash, "startupWordmark");
        var x = word.x, y = word.y;
        wait(1100); verify(art.moving);
        var first = grabImage(art);
        wait(500); verify(!grabImage(art).equals(first));
        compare(word.x, x); compare(word.y, y);
        splash.stage = 6;
        wait(20); verify(!art.moving);
        splash.stage = 2;
        wait(20); verify(art.moving);
        splash.reducedMotion = true;
        wait(20); verify(!art.moving);
        compare(art.drift, 0);
        splash.destroy();
    }

    function test_global_theme_resolves_dagric_splash() {
        var c = Qt.createComponent("../../config/includes.chroot/usr/share/plasma/look-and-feel/org.dagric.desktop/contents/splash/Splash.qml");
        compare(c.status, Component.Ready, c.errorString());
        var splash = c.createObject(wizard.contentItem, {width:800,height:600,stage:1,
            motionSettingsUrl: Qt.resolvedUrl("../fixtures/motion-disabled.ini")});
        verify(splash !== null);
        compare(splash.stage, 1);
        compare(splash.motionFactor, 0); // actual INI read, not a simulated flag
        splash.motionFactor = 0;
        verify(splash.reducedMotion);
        splash.motionFactor = 1;
        verify(!splash.reducedMotion);
        splash.stage = 6;
        wait(250);
        splash.reducedMotion = true;
        compare(splash.reducedMotion, true);
        var art = findChild(splash, "startupAperture");
        verify(art !== null);
        verify(!art.moving);
        compare(art.reveal, 1);
        compare(splash.progress, 1);
        splash.stage = -1;
        compare(splash.progress, 0);
        splash.stage = 6;
        var splashPath = decodeURIComponent(Qt.resolvedUrl("../../out/aperture-startup-800.png").toString().replace("file://", ""));
        grabImage(splash).save(splashPath);
        splash.destroy();
    }

    function test_page_matrix_data() {
        return [{tag:"small",w:800,h:600,edition:"free"},
                {tag:"laptop",w:1366,h:768,edition:"free"},
                {tag:"desktop",w:1920,h:1080,edition:"free"},
                {tag:"pro-small",w:800,h:600,edition:"pro"},
                {tag:"pro-laptop",w:1366,h:768,edition:"pro"},
                {tag:"pro-desktop",w:1920,h:1080,edition:"pro"},
                {tag:"pro-light",w:1366,h:768,edition:"pro",mode:"light"},
                {tag:"pro-large-text",w:1024,h:768,edition:"pro",ui:1.5},
                {tag:"compact",w:360,h:400,edition:"free"}];
    }
    function test_page_matrix(data) {
        wizard.edition=data.edition;
        wizard.editionName=data.edition === "pro" ? "Dagric OS Pro" : "Dagric OS";
        wizard.width=data.w; wizard.height=data.h;
        wizard.mode=data.mode || "dark";
        if (data.ui) wizard.ui=data.ui;
        for(var i=0;i<wizard.steps.length;i++) {
            wizard.stepIndex=i;
            wait(220);
            compare(wizard.loadError, "");
            verify(wizard.width <= data.w);
            verify(wizard.height <= data.h);
            var next = findChild(wizard.contentItem, "setupNext");
            verify(next !== null);
            var p = next.mapToItem(wizard.contentItem, 0, 0);
            verify(p.x >= 0 && p.y >= 0);
            verify(p.x + next.width <= wizard.width + 1);
            verify(p.y + next.height <= wizard.height + 1);
            if (wizard.step === "welcome") {
                var hero = findChild(wizard.contentItem, "welcomeApertureCard");
                verify(hero !== null);
                if (hero.visible) {
                    var h = hero.mapToItem(wizard.contentItem, 0, 0);
                    verify(h.x >= 0 && h.x + hero.width <= wizard.width + 1);
                    verify(h.y >= 0 && h.y + hero.height <= wizard.height + 1);
                }
                var welcomePath = decodeURIComponent(Qt.resolvedUrl("../../out/aperture-welcome-"+data.tag+".png").toString().replace("file://", ""));
                grabImage(wizard.contentItem).save(welcomePath);
            }
            if (wizard.step === "display") {
                wizard.scaleTrial = true;
                wizard.scaleSeconds = 20;
                wait(250);
                var keep = findChild(wizard.contentItem, "keepSize");
                var k = keep.mapToItem(wizard.contentItem, 0, 0);
                verify(keep.visible);
                verify(k.x >= 0 && k.x + keep.width <= wizard.width + 1);
                verify(k.y >= 0 && k.y + keep.height <= wizard.height + 1);
                var imagePath = decodeURIComponent(Qt.resolvedUrl("../../out/firstrun-qa-20260905-"+data.tag+".png").toString().replace("file://", ""));
                grabImage(wizard.contentItem).save(imagePath);
                wizard.scaleTrial = false;
            }
        }
    }
}
