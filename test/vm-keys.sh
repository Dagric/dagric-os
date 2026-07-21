#!/bin/sh
# Send each argument as a QEMU sendkey, with a small delay between keys.
#   sh /vm-keys.sh l i v e ret
for k in "$@"; do
    printf 'sendkey %s\n' "$k" | socat - UNIX-CONNECT:/tmp/monitor.sock >/dev/null
    sleep 0.5
done
