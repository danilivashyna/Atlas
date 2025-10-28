# Atlas CI/CD Workflows

This directory contains GitHub Actions workflows for automated testing, validation, and deployment.

## Workflows

### E4 GA Validation (`e4-ga-validation.yml`)

**Purpose:** Automated validation of E4 Homeostasis components against GA quality standards.

**Triggers:**
- Push to `main` branch
- Push to `release/**` branches
- Push to `feature/E4-**` branches
- Pull requests to `main`

**Jobs:**

1. **e4-validation** (Matrix: Python 3.11, 3.12)
   - Runs all 112 E4 tests across 9 components
   - Validates SLO compliance (rollback time ≤30s)
   - Generates coverage reports
   - Timeout: 10 minutes per job

2. **e4-slo-report**
   - Aggregates test results from all Python versions
   - Generates SLO compliance report (markdown)
   - Uploads artifacts with 90-day retention

3. **e4-lint-check**
   - Runs ruff linter on E4 modules
   - Checks code formatting
   - Non-blocking (continue-on-error)

**Components Tested:**

| Component | Tests | File | Timeout |
|-----------|-------|------|---------|
| E4.1 Policy Engine | 18 | `test_policy_engine.py` | 2 min |
| E4.2 Decision Engine | 11 | `test_decision_engine.py` | 2 min |
| E4.3 Action Adapters | 16 | `test_actions.py` | 2 min |
| E4.5 Audit Logger | 13 | `test_audit.py` | 2 min |
| E4.4 Snapshot & Rollback | 14 | `test_snapshot.py` | 3 min (SLO critical) |
| E4.8 Homeostasis Metrics | 7 | `test_homeostasis_metrics.py` | 2 min |
| E4.7 API Routes | 13 | `test_homeostasis_routes.py` | 2 min |
| E4.7 Integration | 7 | `test_homeostasis_integration.py` | 2 min |
| E4.6 Sleep & Consolidation | 13 | `test_sleep.py` | 3 min |

**SLO Validation:**

The workflow explicitly validates:
- ✅ **Rollback Time:** E4.4 snapshot rollback must complete in ≤30s (measured <1s)
- ✅ **Test Pass Rate:** 112/112 tests must pass (100%)
- ✅ **API Functionality:** All 5 homeostasis routes must respond correctly

**Artifacts:**

- `e4-ga-validation-py3.11/` - Test results for Python 3.11
- `e4-ga-validation-py3.12/` - Test results for Python 3.12
- `e4-slo-report/` - SLO compliance summary (90-day retention)

**Coverage:**

Coverage reports are uploaded to Codecov with:
- Flag: `e4-homeostasis`
- Paths: `src/atlas/homeostasis/`, `src/atlas/metrics/homeostasis.py`
- Format: XML + terminal output with missing lines

## Local Testing

To run the same validation locally:

```bash
# Install dev dependencies
pip install -e ".[dev]"
pip install pytest pytest-cov pytest-timeout

# Run full E4 suite
pytest tests/ -v -k "policy_engine or decision_engine or actions or audit or snapshot or homeostasis_metrics or homeostasis_routes or homeostasis_integration or sleep" --durations=20

# Run with coverage
pytest tests/ -k "homeostasis or snapshot or sleep or metrics" --cov=src/atlas/homeostasis --cov=src/atlas/metrics/homeostasis --cov-report=term-missing

# Validate SLO (rollback time)
pytest tests/test_snapshot.py::TestSnapshotManager::test_rollback -v --durations=0
```

## Monitoring

Check workflow status:
- GitHub Actions tab: https://github.com/danilivashyna/Atlas/actions
- Latest runs: Filter by "E4 GA Validation"
- Artifacts: Download from successful runs (retention: 30-90 days)

## Troubleshooting

**Timeout errors:**
- Individual test steps have 2-3 minute timeouts
- Full suite has 10 minute timeout
- If exceeded, check for hanging tests or slow CI runners

**Flaky tests:**
- E4 tests are deterministic with mocked dependencies
- Random failures likely indicate environment issues (disk I/O, memory)
- Re-run the workflow to confirm

**Coverage failures:**
- Coverage upload is non-blocking (`fail_ci_if_error: false`)
- Check Codecov integration if reports aren't appearing

## Future Enhancements

Planned additions:
- Integration tests with real Redis/PostgreSQL (v0.3)
- Performance regression detection
- Automated release tagging on passing GA validation
- Deployment to staging environment
- Production telemetry SLO monitoring (repair success, false positives)
