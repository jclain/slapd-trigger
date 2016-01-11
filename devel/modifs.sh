#!/bin/bash
# -*- coding: utf-8 mode: sh -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8
cd "$(dirname -- "$0")"
until="$1"
for i in ldif*; do
    num="${i%%-*}"; num="${num#ldif}"
    action="${i##*-}"
    cmd=("ldap$action" -Y EXTERNAL -f "$i")
    echo "$ ${cmd[*]}"
    sudo "${cmd[@]}"
    [ "$num" == "$until" ] && break
done
