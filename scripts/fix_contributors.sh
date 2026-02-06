#!/usr/bin/env bash
# Contributors me sirf tumhara naam aaye – commit messages se "Co-authored-by: Cursor" hata ke force push.
# Jab bhi Cursor se commit karke push kiya aur cursoragent Contributors me aa gaya, ye script chalao.

set -e
cd "$(git rev-parse --show-toplevel)"

echo "Stashing uncommitted changes (if any)..."
git stash push -m "fix_contributors_temp" 2>/dev/null || true

echo "Removing 'Co-authored-by:' from all commit messages..."
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --msg-filter 'sed "/^Co-authored-by:/d"' -- --all

echo "Force pushing to origin main..."
git push --force origin main

echo "Restoring stashed changes (if any)..."
git stash pop 2>/dev/null || true

echo "Done. GitHub pe Contributors 1–2 min me update ho jayega. Page refresh karo."
