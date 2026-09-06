// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Window
import QtTest

TestCase {
    id: test
    name: "DagricInstallerDesktop"
    when: windowShown
    visible: true
    width: 900; height: 700
    QtObject { id: config; property string packageChoice: "" }
    property var page
    function init() {
        config.packageChoice = ""
        var component = Qt.createComponent("../../config/includes.chroot/etc/calamares/branding/dagric/dagricdesktop.qml")
        compare(component.status, Component.Ready, component.errorString())
        page = component.createObject(test, {width:820,height:600,assetBase:Qt.resolvedUrl("../../config/includes.chroot/usr/share").toString()})
        verify(page !== null)
    }
    function cleanup() { if (page) page.destroy() }
    function test_default_and_all_choices() {
        compare(config.packageChoice, "Dark · Centered · Modern icons · 100% text · Obsidian")
        var modes=["dark","light"], layouts=["classic","eleven"], icons=["modern","classic","old-school"], sizes=["normal","bigger","biggest"], walls=["obsidian","arctic","aurora"]
        var count=0
        for(var m of modes) for(var l of layouts) for(var i of icons) for(var s of sizes) for(var w of walls) {
            page.mode=m; page.layout=l; page.icons=i; page.textSize=s; page.wallpaper=w
            compare(config.packageChoice, page.profile); verify(config.packageChoice.indexOf("undefined") < 0); count++
        }
        compare(count,108)
    }
    function test_selection_visible_and_keyboard() {
        var c=Qt.createComponent("../../config/includes.chroot/etc/calamares/branding/dagric/ProfileChoice.qml")
        compare(c.status,Component.Ready,c.errorString())
        var choice=c.createObject(test,{text:"Bigger · 125%",detail:"Easier to read",selected:true,x:10,y:10})
        verify(choice.Accessible.name.indexOf("selected")>=0)
        choice.forceActiveFocus(); verify(choice.activeFocus)
        choice.destroy()
    }
    function test_recommended_customize_and_persistent_preview() {
        compare(page.customizing, false)
        var button=findChild(page,"customize")
        button.forceActiveFocus(); keyClick(Qt.Key_Space)
        compare(page.customizing,true)
        page.width=520; page.height=420; page.mode="light"; page.textSize="biggest"
        wait(50)
        var preview=findChild(page,"persistentPreview"), scroll=findChild(page,"choicesScroll")
        var y=preview.mapToItem(page,0,0).y
        scroll.contentItem.contentY=250
        wait(50)
        compare(preview.mapToItem(page,0,0).y,y)
        verify(preview.height>=110); verify(page.color.r>0.8)
        var image=grabImage(page)
        image.save(decodeURIComponent(Qt.resolvedUrl("../../out/installer-customize-small.png").toString().replace("file://","")))
        page.useRecommended()
        compare(page.customizing,false); compare(page.textSize,"normal")
        compare(config.packageChoice,"Dark · Centered · Modern icons · 100% text · Obsidian")
    }
    function test_back_retains_choices() {
        page.mode="light"; page.textSize="biggest"; page.layout="classic"
        page.destroy()
        var c=Qt.createComponent("../../config/includes.chroot/etc/calamares/branding/dagric/dagricdesktop.qml")
        page=c.createObject(test,{width:640,height:420,assetBase:Qt.resolvedUrl("../../config/includes.chroot/usr/share").toString()})
        compare(page.mode,"light"); compare(page.textSize,"biggest"); compare(page.layout,"classic")
        compare(page.textPercent,150)
    }
    function test_controls_page_loads_and_resizes() {
        var c=Qt.createComponent("../../config/includes.chroot/usr/share/dagric/desktop-settings/main.qml")
        compare(c.status,Component.Ready,c.errorString())
        var center=c.createObject(null,{width:480,height:420,assetBase:Qt.resolvedUrl("../../config/includes.chroot/usr/share").toString()})
        verify(center!==null); compare(center.actions.length,5)
        center.requestAction("evil command")
        wait(50); center.destroy()
    }
    function test_visual_preview() {
        page.width=820; page.height=660
        wait(300)
        var path=decodeURIComponent(Qt.resolvedUrl("../../out/installer-desktop-preview.png").toString().replace("file://",""))
        var captured=grabImage(page)
        compare(captured.width,820); compare(captured.height,660)
        captured.save(path)
        page.width=520; page.height=420; page.mode="light"; page.textSize="biggest"; page.wallpaper="arctic"
        wait(300)
        path=decodeURIComponent(Qt.resolvedUrl("../../out/installer-desktop-small-preview.png").toString().replace("file://",""))
        captured=grabImage(page); compare(captured.width,520); compare(captured.height,420)
        captured.save(path)
    }
}
