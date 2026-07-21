#!/bin/sh
# Click at absolute pixel coordinates via VNC (reliable, unlike monitor mouse_move).
#   sh /vm-vclick.sh X Y
vncdo -s localhost::5900 move "$1" "$2" click 1
