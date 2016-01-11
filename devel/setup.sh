#!/bin/bash
# -*- coding: utf-8 mode: sh -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8
scriptdir="$(cd "$(dirname -- "$0")"; pwd)"
cd "$scriptdir"

setup_load=
setup_conf=
start=
stop=
case "$1" in
setup) setup_load=1; setup_conf=1;;
load) setup_load=1;;
conf) setup_conf=1;;
start) start=1;;
stop) stop=1;;
esac

if [ -n "$setup_load" ]; then
sudo ldapmodify -Y EXTERNAL <<EOF
dn: cn=module{0},cn=config
changetype: modify
add: olcModuleLoad
olcModuleLoad: back_sock.la
-
EOF
fi

if [ -n "$setup_conf" ]; then
sudo ldapmodify -Y EXTERNAL <<EOF
dn: olcOverlay=sock,olcDatabase={2}mdb,cn=config
changetype: add
objectClass: olcConfig
objectClass: olcOverlayConfig
objectClass: olcOvSocketConfig
olcOverlay: sock
olcDbSocketPath: $scriptdir/slapd-trigger.sock
olcOvSocketOps: modify modrdn add delete
olcDbSocketExtensions: binddn peername ssf connid
#olcOvSocketResps: 
EOF
fi

if [ -n "$start" ]; then
sudo ldapmodify -Y EXTERNAL <<EOF
dn: olcOverlay=sock,olcDatabase={2}mdb,cn=config
changetype: modify
replace: olcOvSocketOps
olcOvSocketOps: modify modrdn add delete
-
EOF
fi

if [ -n "$stop" ]; then
sudo ldapmodify -Y EXTERNAL <<EOF
dn: olcOverlay=sock,olcDatabase={2}mdb,cn=config
changetype: modify
replace: olcOvSocketOps
olcOvSocketOps: NONE
-
EOF
fi
