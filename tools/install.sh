#!/usr/bin/env bash
# Install (symlink or copy) the skills of this repository into an agent's skill directory.
#
#   tools/install.sh claude-user                # ~/.claude/skills
#   tools/install.sh claude-project DIR         # DIR/.claude/skills
#   tools/install.sh codex-user                 # ~/.agents/skills
#   tools/install.sh codex-project DIR          # DIR/.agents/skills
# Options (before the target):
#   --copy        copy instead of symlink (symlinks keep installs in sync with this repo)
#   --force       replace an existing entry with the same name
#   --uninstall   remove entries that point into this repository
#
# Note: a user-level install makes the skill descriptions visible to every agent session that
# runs under your account, including automated research harnesses. Prefer a project-level
# install if such harnesses share the account and should not see these skills.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE=link FORCE=0 UNINSTALL=0
while [[ $# -gt 0 && "$1" == --* ]]; do
  case "$1" in
    --copy) MODE=copy ;;
    --force) FORCE=1 ;;
    --uninstall) UNINSTALL=1 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
  shift
done
TARGET="${1:-}"
case "$TARGET" in
  claude-user) DEST="$HOME/.claude/skills" ;;
  claude-project) DEST="${2:?project dir required}/.claude/skills" ;;
  codex-user) DEST="$HOME/.agents/skills" ;;
  codex-project) DEST="${2:?project dir required}/.agents/skills" ;;
  *) sed -n '2,18p' "$0"; exit 2 ;;
esac

python3 "$REPO/tools/sync_shared.py" --check >/dev/null || {
  echo "shared copies are out of sync; run: python3 $REPO/tools/sync_shared.py" >&2; exit 1; }

mkdir -p "$DEST"
for skill in "$REPO"/skills/*/; do
  name="$(basename "$skill")"
  dst="$DEST/$name"
  if [[ $UNINSTALL -eq 1 ]]; then
    if [[ -L "$dst" && "$(readlink -f "$dst")" == "$(readlink -f "$skill")" ]]; then
      rm "$dst"; echo "removed $dst"
    elif [[ -e "$dst" ]]; then
      echo "skip $dst (not a link into this repo; remove it by hand if it is a copy)"
    fi
    continue
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ -L "$dst" && "$(readlink -f "$dst")" == "$(readlink -f "$skill")" ]]; then
      echo "ok   $dst (already linked)"; continue
    fi
    if [[ $FORCE -eq 0 ]]; then
      echo "exists: $dst (use --force to replace)" >&2; exit 1
    fi
    rm -rf "$dst"
  fi
  if [[ $MODE == copy ]]; then
    cp -R "${skill%/}" "$dst"; echo "copied $dst"
  else
    ln -s "${skill%/}" "$dst"; echo "linked $dst -> ${skill%/}"
  fi
done
