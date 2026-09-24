#!/usr/bin/env bash
# Publish the module's new commits from this workspace to SAG's repository
# (github.com/ahmadmessi89-max/legal_department_management), branch
# professional-19.0.7, with the module at the repository root.
#
# Each workspace commit that touched custom_addons/legal_department_management
# is replayed with its own message, author and dates. docs/ldm is copied as a
# separate "docs" commit when it changed. Never touches SAG's main branch.
#
# Usage (from the odoo19 workspace): bash docs/ldm/tools/sync_to_sag.sh [--push]
set -euo pipefail
WORKSPACE="$(git rev-parse --show-toplevel)"
CLONE="/c/Users/Lenovo/Documents/ldm_repo/legal_department_management"
BRANCH="professional-19.0.7"
MARK="$CLONE/.git/ldm_last_synced"

cd "$WORKSPACE"
git branch -f ldm-split "$(git subtree split -q --prefix=custom_addons/legal_department_management main)"

cd "$CLONE"
git remote get-url workspace >/dev/null 2>&1 || git remote add workspace "$WORKSPACE"
git fetch -q workspace ldm-split
git checkout -q "$BRANCH"
last="$(cat "$MARK" 2>/dev/null || true)"
range="workspace/ldm-split"
[ -n "$last" ] && range="$last..workspace/ldm-split"
parent="$(git rev-parse HEAD)"
count=0
for c in $(git rev-list --reverse $range); do
  [ -z "$last" ] && [ "$c" = "$(git rev-list --reverse workspace/ldm-split | head -1)" ] && continue
  tree="$(git rev-parse "$c^{tree}")"
  # keep the docs folder that lives only in this repository
  if git cat-file -e "$parent:docs" 2>/dev/null; then
    tree="$(git read-tree --empty && git read-tree "$tree" && git read-tree --prefix=docs/ "$parent:docs" && git write-tree)"
  fi
  export GIT_AUTHOR_NAME="$(git log -1 --format=%an "$c")" GIT_AUTHOR_EMAIL="$(git log -1 --format=%ae "$c")"
  export GIT_AUTHOR_DATE="$(git log -1 --format=%aI "$c")" GIT_COMMITTER_NAME="$(git log -1 --format=%cn "$c")"
  export GIT_COMMITTER_EMAIL="$(git log -1 --format=%ce "$c")" GIT_COMMITTER_DATE="$(git log -1 --format=%cI "$c")"
  parent="$(git log -1 --format=%B "$c" | git commit-tree "$tree" -p "$parent")"
  count=$((count + 1))
done
git reset -q --hard "$parent"
git rev-parse workspace/ldm-split > "$MARK"
unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_AUTHOR_DATE GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL GIT_COMMITTER_DATE

# docs/ldm -> docs/ldm: exactly what is committed in the workspace, so
# uncommitted screenshots and scratch files stay behind and a document removed
# there is removed here; its own commit when it changed
rm -rf docs/ldm
git -C "$WORKSPACE" archive HEAD docs/ldm | tar -x -f -
if [ -n "$(git status --porcelain docs)" ]; then
  git add -A docs
  git commit -q -m "docs: state, evidence and tools brought up to date"
  count=$((count + 1))
fi
echo "$count commit(s) added to $BRANCH"
git log --oneline -3
if [ "${1:-}" = "--push" ]; then git push -q origin "$BRANCH" && echo "pushed $BRANCH"; fi
