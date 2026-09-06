// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtTest

TestCase {
    id: test
    name: "DagricDesktopControls"
    when: windowShown
    visible: true
    width: 900; height: 900
    property var controls
    QtObject {
        id: bridge
        signal result(string response)
        property var requests: []
        property bool fail: false
        property var panel: ({id:7, screen:0, height:48, location:"bottom", alignment:"center", floating:true, hiding:"none", lengthMode:"fill"})
        function request(action, payload) {
            requests.push({action:action, payload:JSON.parse(payload)})
            if (fail) { result(JSON.stringify({ok:false, message:"Test: desktop is unavailable"})); return }
            if (action === "query") result(JSON.stringify({ok:true, panels:[panel], pending:false, canUndoLayout:true}))
            else if (action === "keep" || action === "revert") result(JSON.stringify({ok:true,message:action === "keep" ? "Kept" : "Restored"}))
            else result(JSON.stringify({ok:true,pending:true,seconds:60,message:"Trial started"}))
        }
    }
    function findText(item, text) {
        if (item.text === text) return item
        if (item.children) for (var child of item.children) {
            var match=findText(child,text); if (match) return match
        }
        return null
    }
    function init() {
        bridge.requests=[]; bridge.fail=false
        var c=Qt.createComponent("../../config/includes.chroot/usr/share/dagric/desktop-settings/PanelControls.qml")
        compare(c.status,Component.Ready,c.errorString())
        controls=c.createObject(test,{bridge:bridge,width:600})
        verify(controls!==null)
        compare(bridge.requests[0].action,"query")
        compare(controls.panels.length,1)
        compare(controls.busy,false)
    }
    function cleanup() { if(controls) controls.destroy() }
    function test_taskbar_labels_use_visible_order_not_internal_plasma_ids() {
        var selector=findChild(controls,"panelSelector")
        verify(selector!==null)
        compare(selector.currentText,"Taskbar 1 · screen 1")
        controls.apply()
        compare(bridge.requests[bridge.requests.length-1].payload.id,7)
    }
    function test_apply_has_exact_allowlisted_payload_and_locks_controls() {
        controls.apply()
        var request=bridge.requests[bridge.requests.length-1]
        compare(request.action,"apply"); compare(request.payload.id,7)
        compare(Object.keys(request.payload.values).sort().join(","),"alignment,floating,height,hiding,lengthMode,location")
        compare(request.payload.values.height,48)
        compare(controls.pending,true); compare(controls.seconds,60)
        verify(!findText(controls,"Try these settings").enabled)
        controls.request("revert")
        compare(controls.pending,false)
        verify(bridge.requests.some(function(r){return r.action==="revert"}))
        compare(bridge.requests[bridge.requests.length-1].action,"query")
    }
    function test_errors_do_not_claim_a_successful_preview() {
        bridge.fail=true; controls.apply()
        compare(controls.pending,false); compare(controls.busy,false)
        verify(controls.message.indexOf("unavailable")>=0)
    }
    function test_layout_reset_requires_explicit_checkbox() {
        var button=findText(controls,"Preview default layout")
        verify(button!==null); verify(!button.enabled)
        var confirmation=findText(controls,"I want to reset my desktop layout")
        confirmation.checked=true
        verify(button.enabled)
        button.clicked()
        compare(bridge.requests[bridge.requests.length-1].action,"reset-layout")
        compare(confirmation.checked,false); compare(controls.pending,true)
    }
    function test_disabled_without_native_bridge() {
        controls.destroy()
        var c=Qt.createComponent("../../config/includes.chroot/usr/share/dagric/desktop-settings/PanelControls.qml")
        controls=c.createObject(test,{width:480})
        verify(!findText(controls,"Try these settings").enabled)
        verify(!findText(controls,"Preview default layout").enabled)
        verify(controls.message.indexOf("runner")>=0)
    }
}
