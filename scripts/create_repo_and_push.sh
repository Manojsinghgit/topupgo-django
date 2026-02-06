#!/usr/bin/env bash
# Create GitHub repo and push. Needs: gh CLI (brew install gh && gh auth login) OR GITHUB_TOKEN.

set -e
REPO_NAME="${1:-topupgo-django}"
GITHUB_USER="${GITHUB_USER:-}"

if command -v gh &>/dev/null; then
  echo "Using GitHub CLI (gh)..."
  gh repo create "$REPO_NAME" --public --source=. --remote=origin --push
  echo "Done. Repo: https://github.com/$(gh api user -q .login)/$REPO_NAME"
  exit 0
fi

if [ -z "$GITHUB_TOKEN" ]; then
  echo "No 'gh' and no GITHUB_TOKEN. Options:"
  echo "  1) Install GitHub CLI: brew install gh && gh auth login"
  echo "     Then run: ./scripts/create_repo_and_push.sh"
  echo "  2) Create repo on https://github.com/new (name: $REPO_NAME), then:"
  echo "     git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
  echo "     git push -u origin main"
  exit 1
fi

# Get username from API
GITHUB_USER="${GITHUB_USER:-$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin).get('login',''))")}"
if [ -z "$GITHUB_USER" ]; then
  echo "Could not get GitHub username. Set GITHUB_USER=your_username"
  exit 1
fi

echo "Creating repo $REPO_NAME for $GITHUB_USER..."
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/user/repos" -d "{\"name\":\"$REPO_NAME\",\"private\":false}" >/dev/null

if git remote get-url origin &>/dev/null; then
  git remote remove origin
fi
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
git push -u origin main
echo "Done. Repo: https://github.com/$GITHUB_USER/$REPO_NAME"
