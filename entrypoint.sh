#!/bin/bash

prefix="FILE__"

while IFS='=' read -r var path; do
    name=${var#$prefix}
    value=$(cat "${path}")
    export "${name}"="${value}"
    unset "${var}"
done < <(env | grep "^${prefix}")

exec -- "$@"