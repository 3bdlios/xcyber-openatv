#!/bin/sh
set -eu
prefix="${1:-}"
config="$prefix/etc/pam.d/common-password"
[ -f "$config" ] || exit 0
# Some /bin/sh implementations print echo -e's option literally.
# This repairs only that malformed PAM password line and preserves the stack.
if grep -q '^-e[[:space:]][[:space:]]*password[[:space:]]' "$config"; then
    sed -i 's/^-e[[:space:]][[:space:]]*password/password/' "$config"
fi
