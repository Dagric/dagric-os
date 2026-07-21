#!/bin/sh
# Click at pixel coordinates on the VM screen (USB tablet = absolute pointer).
#   sh /vm-click.sh X Y [SCREEN_W] [SCREEN_H]
X=$1; Y=$2; W=${3:-1280}; H=${4:-800}
AX=$((X * 32767 / W))
AY=$((Y * 32767 / H))
{
    printf 'mouse_move %s %s\n' "$AX" "$AY"
    sleep 0.4
    printf 'mouse_button 1\n'
    sleep 0.2
    printf 'mouse_button 0\n'
} | socat - UNIX-CONNECT:/tmp/monitor.sock >/dev/null
