// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtTest
TestCase {
    name: "SplashPreview"
    when: windowShown
    visible: true
    width: 400; height: 225
    function test_render() {
        var c = Qt.createComponent("../../config/includes.chroot/usr/share/plasma/look-and-feel/org.dagric.splash/contents/splash/Splash.qml");
        compare(c.status, Component.Ready, c.errorString());
        var splash = c.createObject(this, {width:400, height:225, stage:3,
            reducedMotion:true, motionSettingsUrl:Qt.resolvedUrl("../../test/fixtures/motion-disabled.ini")});
        verify(splash !== null);
        wait(100);
        var path = decodeURIComponent(Qt.resolvedUrl("../../config/includes.chroot/usr/share/plasma/look-and-feel/org.dagric.splash/contents/previews/splash.png").toString().replace("file://", ""));
        var capture = grabImage(splash);
        compare(capture.width, 400);
        compare(capture.height, 225);
        capture.save(path);
        splash.destroy();
    }
}
