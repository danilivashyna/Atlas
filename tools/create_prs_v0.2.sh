#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./tools/create_prs_v0.2.sh                 # по умолчанию danilivashyna/Atlas
#   ./tools/create_prs_v0.2.sh owner/repo      # явно указать репозиторий
#
# Требования:
#   - GitHub CLI: https://cli.github.com/
#   - Выполнен `gh auth login` с правами на репо

REPO="${1:-danilivashyna/Atlas}"

BRANCHES=(
  "feature/v0.2-01-encoder-bert"
  "feature/v0.2-02-decoder-transformer"
  "feature/v0.2-03-api-hier-ops"
  "feature/v0.2-04-losses-hier"
  "feature/v0.2-05-distill-teacher"
  "feature/v0.2-06-metrics-hier"
  "feature/v0.2-07-benchmarks"
  "feature/v0.2-08-docs-demos-cli"
)

# ---- helpers ----

title_for() {
  case "$1" in
    feature/v0.2-01-encoder-bert)
      echo "v0.2-01: Implement TextEncoder5D (BERT-based 5D encoder)";;
    feature/v0.2-02-decoder-transformer)
      echo "v0.2-02: Interpretable Transformer Decoder (5D→text)";;
    feature/v0.2-03-api-hier-ops)
      echo "v0.2-03: Hierarchical API endpoints (/encode_h, /decode_h, /explain_h)";;
    feature/v0.2-04-losses-hier)
      echo "v0.2-04: Hierarchical losses (orthogonality, sparsity, β-TC)";;
    feature/v0.2-05-distill-teacher)
      echo "v0.2-05: Teacher→Student distillation pipeline";;
    feature/v0.2-06-metrics-hier)
      echo "v0.2-06: Metrics — H-Coherence, H-Stability, H-Diversity";;
    feature/v0.2-07-benchmarks)
      echo "v0.2-07: Benchmarks suite (latency, reconstruction, interpretability)";;
    feature/v0.2-08-docs-demos-cli)
      echo "v0.2-08: Docs, demos, CLI updates for hierarchical v0.2";;
  esac
}

body_for() {
  case "$1" in
    feature/v0.2-01-encoder-bert) cat <<'EOF'
**Goal**
Implement `TextEncoder5D` using MiniLM embeddings with 384→5D projection.

**Scope**
- Add `src/atlas/encoders/text_encoder_5d.py`
- Integrate encoder with `/encode` and `/encode_h`
- Unit tests: `tests/test_text_encoder_5d.py`
- Low-latency CPU path (warm p95 < 80ms)

**Checklist**
- [x] Encoder skeleton
- [x] Unit tests
- [ ] Benchmarks & docs

**Refs:** `FEATURE_BRANCHES_v0.2.md`, `docs/HIERARCHICAL_SCHEMA_v0.2.md`
EOF
      ;;
    feature/v0.2-02-decoder-transformer) cat <<'EOF'
**Goal**
Interpretable Transformer-based decoder for 5D→text with reasoning.

**Scope**
- `src/atlas/decoders/interpretable_decoder.py`
- Reasoning trace (per-dimension / per-path)
- `/decode`, `/decode_h` integration
- Metrics: BLEU/ROUGE sanity

**Checklist**
- [x] Decoder skeleton
- [ ] Reasoning validation
- [ ] Docs & examples

**Refs:** `FEATURE_BRANCHES_v0.2.md`
EOF
      ;;
    feature/v0.2-03-api-hier-ops) cat <<'EOF'
**Goal**
Extend FastAPI with hierarchical ops: `/encode_h`, `/decode_h`, `/explain_h`.

**Scope**
- Pydantic schemas (v2) for hierarchical tree
- OpenAPI docs & examples
- CLI parity

**Checklist**
- [x] Endpoints
- [ ] OpenAPI validation
- [ ] CLI parity

**Refs:** `src/atlas/api/app.py`, `docs/HIERARCHICAL_SCHEMA_v0.2.md`
EOF
      ;;
    feature/v0.2-04-losses-hier) cat <<'EOF'
**Goal**
Implement hierarchical losses for disentanglement.

**Scope**
- Orthogonality + L1 sparsity + router entropy
- β-TC-VAE-style components
- Training integration

**Checklist**
- [x] Losses implemented
- [ ] Convergence verified
- [ ] Docstrings & docs

**Refs:** `src/atlas/training/losses_hier.py`
EOF
      ;;
    feature/v0.2-05-distill-teacher) cat <<'EOF'
**Goal**
Teacher→Student distillation for hierarchical space.

**Scope**
- Teacher checkpoint loader
- Distillation losses & curriculum
- Eval harness

**Checklist**
- [ ] Teacher validated
- [ ] Loss stable
- [ ] Metrics tracked

**Refs:** `src/atlas/training/distill.py`
EOF
      ;;
    feature/v0.2-06-metrics-hier) cat <<'EOF'
**Goal**
Add H-Coherence, H-Stability, H-Diversity metrics.

**Scope**
- `src/atlas/metrics/metrics_hier.py`
- Reporting in CI/benchmarks
- Minimal visualizations

**Checklist**
- [x] H-Coherence
- [ ] H-Stability
- [ ] CI reporting

**Refs:** `docs/METRICS_v0.2.md`
EOF
      ;;
    feature/v0.2-07-benchmarks) cat <<'EOF'
**Goal**
Unified benchmarks for latency, reconstruction, interpretability.

**Scope**
- Dataset configs
- `pytest-benchmark` integration
- CSV/Markdown reports

**Checklist**
- [x] Benchmarks runnable
- [ ] CI wired
- [ ] Results snapshotting

**Refs:** `benchmarks/`, `docs/BENCHMARKS_v0.2.md`
EOF
      ;;
    feature/v0.2-08-docs-demos-cli) cat <<'EOF'
**Goal**
Docs/demos/CLI for hierarchical v0.2.

**Scope**
- README + docs updates
- Demo notebook(s)
- CLI: `atlas explain_h`, `atlas visualize`

**Checklist**
- [x] Docs synced
- [x] CLI help updated
- [ ] Demos finalized

**Refs:** `docs/`, `src/atlas/cli.py`
EOF
      ;;
  esac
}

label_bucket="v0.2"

# ---- run ----

# sanity: auth
if ! gh auth status >/dev/null 2>&1; then
  echo "✖ gh not authenticated. Run: gh auth login"
  exit 1
fi

echo "📋 Creating draft PRs for $REPO..."
echo ""

for BR in "${BRANCHES[@]}"; do
  # Check if PR already exists
  EXISTING_PR=$(gh pr list --repo "$REPO" --head "$BR" --state all --json number -q '.[0].number // empty' 2>/dev/null || true)

  if [[ -n "$EXISTING_PR" ]]; then
    echo "↷ PR #$EXISTING_PR already exists for $BR — skipping."
    continue
  fi

  TITLE="$(title_for "$BR")"
  BODY_FILE="$(mktemp -t pr_body.XXXXXX.md)"
  body_for "$BR" > "$BODY_FILE"

  echo "→ Creating draft PR: $BR"
  if gh pr create \
    --repo "$REPO" \
    --base main \
    --head "$BR" \
    --title "$TITLE" \
    --body-file "$BODY_FILE" \
    --draft >/dev/null 2>&1; then

    PR_NUM=$(gh pr list --repo "$REPO" --head "$BR" --state open --json number -q '.[0].number' 2>/dev/null || true)
    if [[ -n "$PR_NUM" ]]; then
      gh pr edit "$PR_NUM" --repo "$REPO" --add-label "$label_bucket" >/dev/null 2>&1 || true
      echo "✓ Draft PR #$PR_NUM created for $BR"
    else
      echo "⚠ PR likely created for $BR but couldn't resolve number."
    fi
  else
    echo "✗ Failed to create PR for $BR"
  fi

  rm -f "$BODY_FILE"
done

echo ""
echo "✅ Done. Draft PRs prepared."
