#!/bin/sh
# Type a string into the VM via VNC.
#   sh /vm-vtype.sh freehold
vncdo -s localhost::5900 type "$1"
