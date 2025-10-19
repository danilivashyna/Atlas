#!/usr/bin/env bash
set -euo pipefail

# Advanced PR/Issue management for v0.2
# Usage:
#   ./tools/manage_v0.2.sh [command] [args...]
#
# Commands:
#   status          Show current status of all v0.2 PRs and Issues
#   assign <dev>    Assign all v0.2 PRs to developers (round-robin)
#   ready           Convert all draft PRs to ready
#   labels          Add standard labels (v0.2, p1/p2)
#   help            Show this help

REPO="${REPO:-danilivashyna/Atlas}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${BLUE}ℹ${NC}  $*"
}

log_success() {
  echo -e "${GREEN}✅${NC} $*"
}

log_warn() {
  echo -e "${YELLOW}⚠${NC}  $*"
}

log_error() {
  echo -e "${RED}❌${NC} $*"
}

# Check auth
check_auth() {
  if ! gh auth status >/dev/null 2>&1; then
    log_error "gh not authenticated. Run: gh auth login"
    exit 1
  fi
}

# Show v0.2 project status
cmd_status() {
  check_auth

  log_info "v0.2 Project Status"
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  log_info ""
  log_info "📋 Pull Requests:"
  gh pr list --repo "$REPO" -l v0.2 \
    --json number,title,isDraft,state \
    -q '.[] | "\(.number): \(.title) (draft:\(.isDraft), state:\(.state))"' \
    | while read line; do echo "  $line"; done

  log_info ""
  log_info "🎯 Issues:"
  gh issue list --repo "$REPO" -l v0.2 \
    --json number,title,state,labels \
    -q '.[] | "\(.number): \(.title) (state:\(.state))"' \
    | while read line; do echo "  $line"; done

  log_info ""
  log_info "📊 Statistics:"
  local pr_count=$(gh pr list --repo "$REPO" -l v0.2 -q '.[].number' | wc -l)
  local issue_count=$(gh issue list --repo "$REPO" -l v0.2 -q '.[].number' | wc -l)
  echo "  PRs: $pr_count / Issues: $issue_count"
}

# Convert draft PRs to ready
cmd_ready() {
  check_auth

  log_info "Converting draft PRs to ready..."

  for pr_num in $(gh pr list --repo "$REPO" -l v0.2 --search "is:draft" -q '.[] | .number'); do
    log_info "  Converting PR #$pr_num to ready..."
    gh pr ready "$pr_num" --repo "$REPO" 2>/dev/null || log_warn "  Failed to mark PR #$pr_num as ready"
  done

  log_success "Done!"
}

# Add standard labels
cmd_labels() {
  check_auth

  log_info "Adding standard labels to v0.2 PRs..."

  # Ensure labels exist
  for label in "v0.2" "p1" "p2" "help wanted" "good first issue"; do
    gh label create "$label" --description "v0.2.0 release" --color 0075ca \
      --repo "$REPO" 2>/dev/null || true
  done

  # Add to PRs
  for pr_num in $(gh pr list --repo "$REPO" -l v0.2 -q '.[] | .number'); do
    log_info "  PR #$pr_num"
    gh pr edit "$pr_num" --repo "$REPO" --add-label "v0.2" 2>/dev/null || true
  done

  log_success "Done!"
}

# Assign PRs round-robin
cmd_assign() {
  check_auth

  if [[ $# -lt 2 ]]; then
    log_error "Usage: ./tools/manage_v0.2.sh assign <dev1,dev2,dev3...>"
    exit 1
  fi

  local devs=("${2//,/ }")  # Split by comma
  local dev_index=0

  log_info "Assigning PRs round-robin to developers..."

  for pr_num in $(gh pr list --repo "$REPO" -l v0.2 -q '.[] | .number' | sort -n); do
    local dev="${devs[$((dev_index % ${#devs[@]}))]}"

    log_info "  Assigning PR #$pr_num to @$dev"
    gh pr edit "$pr_num" --repo "$REPO" --add-assignee "$dev" 2>/dev/null || log_error "  Failed"

    ((dev_index++))
  done

  log_success "Done!"
}

# Request review from maintainers
cmd_review_request() {
  check_auth

  local reviewer="${1:-danilivashyna}"

  log_info "Requesting review from @$reviewer on all v0.2 PRs..."

  for pr_num in $(gh pr list --repo "$REPO" -l v0.2 -q '.[] | .number'); do
    log_info "  PR #$pr_num"
    gh pr edit "$pr_num" --repo "$REPO" --add-reviewer "$reviewer" 2>/dev/null || log_warn "  Failed"
  done

  log_success "Done!"
}

# Open all v0.2 PRs in browser
cmd_web() {
  check_auth

  log_info "Opening v0.2 PRs in browser..."

  for pr_num in $(gh pr list --repo "$REPO" -l v0.2 -q '.[] | .number'); do
    gh pr view "$pr_num" --repo "$REPO" --web 2>/dev/null || log_warn "Failed to open PR #$pr_num"
    sleep 0.5  # Avoid opening too many tabs at once
  done
}

# Show help
cmd_help() {
  cat << 'EOF'
🔧 v0.2 Project Management Tool

Usage:
  ./tools/manage_v0.2.sh [COMMAND] [ARGS]

Commands:
  status          Show current status of all v0.2 PRs and Issues
  ready           Convert all draft PRs to ready (make reviewable)
  labels          Ensure all standard labels exist and are applied
  assign <devs>   Assign PRs round-robin to developers
                  Example: assign alice,bob,charlie
  review <dev>    Request review from developer (default: danilivashyna)
  web             Open all v0.2 PRs in browser tabs
  help            Show this help message

Environment:
  REPO            GitHub repository (default: danilivashyna/Atlas)
                  Example: REPO=myorg/myrepo ./tools/manage_v0.2.sh status

Examples:
  # Check project status
  ./tools/manage_v0.2.sh status

  # Assign PRs to team members
  ./tools/manage_v0.2.sh assign alice,bob,charlie

  # Mark all draft PRs as ready for review
  ./tools/manage_v0.2.sh ready

  # Request review from maintainer
  ./tools/manage_v0.2.sh review danilivashyna

  # Open all PRs in browser (macOS)
  ./tools/manage_v0.2.sh web

EOF
}

# Main dispatcher
main() {
  local cmd="${1:-help}"

  case "$cmd" in
    status)
      cmd_status
      ;;
    ready)
      cmd_ready
      ;;
    labels)
      cmd_labels
      ;;
    assign)
      cmd_assign "$@"
      ;;
    review)
      cmd_review_request "${2:-danilivashyna}"
      ;;
    web)
      cmd_web
      ;;
    help|--help|-h)
      cmd_help
      ;;
    *)
      log_error "Unknown command: $cmd"
      cmd_help
      exit 1
      ;;
  esac
}

main "$@"
