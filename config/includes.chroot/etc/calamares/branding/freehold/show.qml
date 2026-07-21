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
            text: "Welcome to Freehold OS.\n\nA freehold is property you own outright.\nThis computer is about to become yours."
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
            text: "No telemetry. No ads. No accounts.\n\nSecurity updates install silently in the background,\nand the machine reboots only when you say so."
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
            text: "Need more software?\n\nOpen Discover to install thousands of apps —\nchosen by you, sandboxed, removable."
        }
    }
}
