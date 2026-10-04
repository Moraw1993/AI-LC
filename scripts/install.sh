#!/bin/sh
set -eu
version=${VERSION:-latest}
root=${AILEARN_INSTALL_ROOT:-${XDG_DATA_HOME:-"$HOME/.local/share"}/AI-LC}
bin=${AILEARN_BIN_DIR:-"$HOME/.local/bin"}
case "$root:$bin" in *'
'*|*"'"*) echo 'Unsupported install path' >&2; exit 1;; esac
case "$root" in /*) ;; *) echo 'Install root must be absolute' >&2; exit 1;; esac
case "$bin" in /*) ;; *) echo 'Bin directory must be absolute' >&2; exit 1;; esac
if [ "$version" = latest ]; then
  version=$(curl -fsSL https://api.github.com/repos/Moraw1993/AI-LC/releases/latest | sed -n 's/.*"tag_name": *"\(v[0-9.]*\)".*/\1/p')
fi
printf '%s\n' "$version" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || { echo 'Invalid version' >&2; exit 1; }
case $(uname -s) in Linux) os=linux;; Darwin) os=macos;; *) echo 'Unsupported OS' >&2; exit 1;; esac
case $(uname -m) in x86_64|amd64) arch=x64;; arm64|aarch64) arch=arm64;; *) echo 'Unsupported architecture' >&2; exit 1;; esac
asset=ailearn-$os-$arch
for path in "$root" "$root/versions" "$root/versions/$version" "$bin"; do
  [ ! -L "$path" ] || { echo 'Redirected install path' >&2; exit 1; }
done
mkdir -p "$root" "$bin" "$root/versions"
stage=$(mktemp -d "$root/.install-XXXXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM
for name in "$asset" "$asset.sha256"; do
  if [ -n "${RELEASE_DIRECTORY:-}" ]; then cp "$RELEASE_DIRECTORY/$name" "$stage/$name"
  else curl -fsSL "https://github.com/Moraw1993/AI-LC/releases/download/$version/$name" -o "$stage/$name"; fi
done
expected=$(cut -d ' ' -f 1 "$stage/$asset.sha256")
printf '%s\n' "$expected" | grep -Eq '^[a-f0-9]{64}$' || { echo 'Invalid checksum' >&2; exit 1; }
if command -v sha256sum >/dev/null; then actual=$(sha256sum "$stage/$asset" | cut -d ' ' -f 1)
else actual=$(shasum -a 256 "$stage/$asset" | cut -d ' ' -f 1); fi
[ "$actual" = "$expected" ] || { echo 'Checksum mismatch' >&2; exit 1; }
chmod +x "$stage/$asset"
[ "$("$stage/$asset" --version)" = "${version#v}" ] || { echo 'Version mismatch' >&2; exit 1; }
target="$root/versions/$version/ailearn"
if [ -e "$root/versions/$version" ]; then
  cmp -s "$stage/$asset" "$target" || { echo 'Existing version differs; preserved' >&2; exit 1; }
else
  mkdir "$stage/payload"
  mv "$stage/$asset" "$stage/payload/ailearn"
  mv "$stage/payload" "$root/versions/$version"
fi
if [ -e "$bin/ailearn" ] || [ -L "$bin/ailearn" ]; then
  [ -L "$bin/ailearn" ] || { echo 'Existing command preserved' >&2; exit 1; }
  case $(readlink "$bin/ailearn") in "$root"/versions/*/ailearn) ;; *) echo 'Existing command preserved' >&2; exit 1;; esac
fi
ln -s "$target" "$stage/ailearn"
mv -f "$stage/ailearn" "$bin/ailearn"
printf 'Installed %s. Add %s to PATH, then run: ailearn config --harness codex\n' "$version" "$bin"
