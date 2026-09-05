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

    function test_global_theme_resolves_dagric_splash() {
        var c = Qt.createComponent("../../config/includes.chroot/usr/share/plasma/look-and-feel/org.dagric.desktop/contents/splash/Splash.qml");
        compare(c.status, Component.Ready, c.errorString());
        var splash = c.createObject(wizard.contentItem, {width:800,height:600,stage:1});
        verify(splash !== null);
        compare(splash.stage, 1);
        splash.stage = 6;
        wait(250);
        splash.destroy();
    }

    function test_page_matrix_data() {
        return [{tag:"small",w:800,h:600},{tag:"laptop",w:1366,h:768},{tag:"desktop",w:1920,h:1080}];
    }
    function test_page_matrix(data) {
        wizard.width=data.w; wizard.height=data.h;
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
