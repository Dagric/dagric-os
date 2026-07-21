#!/bin/sh
# Send one QEMU monitor command (all args joined) and print the response.
#   sh /vm-mon.sh info mice
#   sh /vm-mon.sh mouse_set 1
{ printf '%s\n' "$*"; sleep 2; } | socat - UNIX-CONNECT:/tmp/monitor.sock
