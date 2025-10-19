#!/usr/bin/env bash
set -euo pipefail

# Create 8 GitHub Issues for v0.2 features + link to PRs
# Usage: ./tools/create_issues_v0.2.sh [repo]

REPO="${1:-danilivashyna/Atlas}"

# Helper functions
log_info() {
  echo "ℹ️  $*" >&2
}

log_success() {
  echo "✅ $*" >&2
}

log_error() {
  echo "❌ $*" >&2
}

# Sanity check: auth
if ! gh auth status >/dev/null 2>&1; then
  log_error "gh not authenticated. Run: gh auth login"
  exit 1
fi

log_info "Creating 8 GitHub Issues for $REPO..."
echo ""

# Store issue numbers in a temp file instead of associative array (zsh compatible)
ISSUE_MAP_FILE=$(mktemp)

for issue_def in "${ISSUES[@]}"; do
  IFS='|' read -r PR_NUM TITLE BODY PRIORITY <<< "$issue_def"

  log_info "Creating issue for PR #$PR_NUM: $TITLE"

  # Create issue with labels (convert P1/P2 to p1/p2 using tr)
  LABELS="v0.2,$(echo "$PRIORITY" | tr 'A-Z' 'a-z')"

  ISSUE_RESPONSE=$(gh issue create \
    --repo "$REPO" \
    --title "$TITLE" \
    --body "$BODY" \
    --label "$LABELS" \
    --assignee "danilivashyna" \
    --json number \
    -q '.number' \
    2>/dev/null || echo "")

  if [[ -z "$ISSUE_RESPONSE" ]]; then
    log_error "Failed to create issue: $TITLE"
    continue
  fi

  ISSUE_NUM="$ISSUE_RESPONSE"

  # Store mapping in file
  echo "$PR_NUM|$ISSUE_NUM" >> "$ISSUE_MAP_FILE"

  log_success "Issue #$ISSUE_NUM created for PR #$PR_NUM"

  # Wait a bit to avoid rate limiting
  sleep 1
done

echo ""
log_info "Linking issues to PRs..."

# Link issues to PRs via comments (Relates-to pattern)
while IFS='|' read -r PR_NUM ISSUE_NUM; do
  log_info "Linking PR #$PR_NUM ↔ Issue #$ISSUE_NUM"

  # Add comment to PR linking to issue
  gh pr comment "$PR_NUM" \
    --repo "$REPO" \
    --body "Relates to #$ISSUE_NUM" \
    >/dev/null 2>&1 || log_error "Failed to comment on PR #$PR_NUM"

  # Add comment to issue linking to PR
  gh issue comment "$ISSUE_NUM" \
    --repo "$REPO" \
    --body "Implementation tracked in PR #$PR_NUM" \
    >/dev/null 2>&1 || log_error "Failed to comment on Issue #$ISSUE_NUM"

  sleep 0.5
done < "$ISSUE_MAP_FILE"

echo ""
log_info "Setting up milestone and project (if available)..."

# Try to set milestone v0.2.0-beta on all issues
while IFS='|' read -r PR_NUM ISSUE_NUM; do
  gh issue edit "$ISSUE_NUM" \
    --repo "$REPO" \
    --milestone "v0.2.0-beta" \
    >/dev/null 2>&1 || true  # Milestone might not exist yet

  sleep 0.3
done < "$ISSUE_MAP_FILE"

echo ""
log_success "✅ All 8 issues created and linked!"
log_info ""
log_info "Summary:"
log_info "─────────────────────────────────────────"

while IFS='|' read -r PR_NUM ISSUE_NUM; do
  printf "PR #%-2s ↔ Issue #%-3s\n" "$PR_NUM" "$ISSUE_NUM" >&2
done < "$ISSUE_MAP_FILE"

# Cleanup
rm -f "$ISSUE_MAP_FILE"

echo ""
log_info "Next steps:"
log_info "  1. Review all issues: gh issue list --repo $REPO -l v0.2"
log_info "  2. Assign developers: gh issue edit #N --assignee developer"
log_info "  3. Open in browser: gh issue list --repo $REPO -l v0.2 --web"
