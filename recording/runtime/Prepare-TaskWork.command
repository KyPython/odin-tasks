#!/bin/zsh
# Off-screen dependency setup only. No project tests or repairs are run.
set -eu
if [[ "$(/usr/bin/id -un)" != recorder || "$HOME" != /Users/recorder || "$EUID" == 0 || -n "${SUDO_USER-}${SUDO_UID-}${SUDO_GID-}${SUDO_COMMAND-}" ]]; then
  print -u2 'STOP: sign directly into the Recorder account and run this helper there.'
  exit 1
fi
script_root=${0:A:h}
exec /usr/local/bin/python3 -I "$script_root/PrepareTaskWork.py" "$@"
