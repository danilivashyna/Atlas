# Changelog

All notable changes to Atlas - Semantic Space Control Panel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0a1] - 2025-10-19

### Added

- **Hierarchical 5D Semantic Space (MVP)**
  - `HierarchicalEncoder`: Text → deterministic 5D tree with child nodes
  - `HierarchicalDecoder`: 5D tree → reasoning explanations per dimension
  - `manipulate_path()`: Surgical edits on tree nodes
- **REST API Hierarchical Endpoints**
  - `POST /encode_h`: Encode text to hierarchical tree
  - `POST /decode_h`: Decode tree to text + reasoning
  - `POST /manipulate_h`: Edit tree dimensions
- **Dual Licensing**
  - AGPL-3.0-or-later for open-source use
  - Commercial license option available
  - SPDX headers on all Python files
- **Testing Infrastructure**
  - 6 smoke tests (all passing)
  - `tests/conftest.py` for pytest fixtures
  - API integration test suite
- **Development Tools**
  - Pre-commit hooks (Black formatter)
  - Makefile with 8 build commands
  - .pre-commit-config.yaml
- **Documentation**
  - `docs/HIERARCHICAL_SCHEMA_v0.2.md`: API schemas and examples
  - `docs/GITHUB_ISSUES_v0.2.md`: 8 issues for future development
  - `LOCAL_SETUP_COMPLETE.md`: Local development guide

### Changed

- pyproject.toml: License set to AGPL-3.0-or-later, email updated
- requirements.txt: Added FastAPI, uvicorn, pytest, httpx, pre-commit
- LICENSE: Updated to dual-license model with contact email

### Fixed

- Fixed pyproject.toml email validation errors
- Fixed imports in API models

## [0.2.0a2] - 2025-10-19 (In Development)

### Added

- **v0.2 Feature Branches & Draft PRs** 🚀
  - 8 parallel feature tracks created with skeleton code
  - Draft PRs #5-12 on GitHub ready for team assignment
  - v0.2-01: TextEncoder5D (BERT-based 5D encoder) — PR #5
  - v0.2-02: Transformer Decoder (5D→text + reasoning) — PR #6
  - v0.2-03: Hierarchical API endpoints expansion — PR #7
  - v0.2-04: Hierarchical losses (ortho, sparsity) — PR #8
  - v0.2-05: Teacher→Student distillation pipeline — PR #9
  - v0.2-06: Metrics (H-Coherence, H-Stability) — PR #10
  - v0.2-07: Benchmarks suite (latency, interpretability) — PR #11
  - v0.2-08: Docs, demos, CLI updates — PR #12

### Fixed

- Dynamic version loading via `importlib.metadata` (APP_VERSION)
- Pydantic v2 migration: All models use `ConfigDict` (0 deprecation warnings)
- Timezone-aware UTC timestamps: `datetime.now(timezone.utc)` pattern
- NumPy array comparisons: `np.allclose()` for floating-point tolerance
- Favicon support: StaticFiles mounted on `/static` (404→200)

### Changed

- Test assertions now support dynamic versioning (not hardcoded "0.1.0")
- All Pydantic models comply with v2.0+ ConfigDict syntax
- All timestamps follow ISO 8601 with Z suffix (UTC marker)

## [Unreleased]

### Added
- Comprehensive documentation suite
- FastAPI REST API implementation
- Docker and docker-compose support
- CI/CD pipeline with GitHub Actions
- Comprehensive test suite (64+ tests)
- Golden sample tests for regression detection
- API integration tests
- Input validation and error handling
- Security features (no raw text logging, trace IDs)
- Health check endpoints
- Metrics tracking

### Documentation
- CONTRIBUTING.md - Contribution guidelines
- CODE_OF_CONDUCT.md - Community guidelines
- SECURITY.md - Security policy
- MODEL_CARD.md - Model documentation
- docs/NFR.md - Non-functional requirements
- docs/DATA_CARD.md - Data documentation
- docs/DISENTANGLEMENT.md - Disentanglement methodology
- docs/INTERPRETABILITY_METRICS.md - Interpretability metrics
- Updated README with status table

## [0.1.0] - 2025-01-19

### Added
- Initial release of Atlas Semantic Space Control Panel
- Simple rule-based encoder for 5D semantic space
- Interpretable decoder with reasoning
- 5 semantic dimensions (Object/Action, Positive/Negative, Abstract/Concrete, I/World, Living/Mechanical)
- Python API (`SemanticSpace` class)
- Command-line interface (`atlas` command)
- Basic visualization capabilities
- Dimension mapping and interpretation
- Text manipulation operations (interpolation, exploration)

### Core Features
- Encode text to 5D vectors
- Decode vectors to text with explanations
- Transform and manipulate semantic dimensions
- Interpolate between concepts
- Explore dimension effects

### Testing
- 29 initial unit tests
- Tests for encoder, decoder, space, dimensions
- 100% passing rate

### Documentation
- README with quick start guide
- DOCUMENTATION.md with full API reference
- Example scripts
- Basic usage documentation

## Release Planning

### [0.2.0] - Planned

**Theme**: Neural Models & Disentanglement

#### Features
- Neural encoder (BERT-based)
- Neural decoder (Transformer)
- Disentanglement training (β-TC-VAE)
- Improved dimension stability
- Model checkpoints with SHA-256 hashes

#### Metrics
- Dim-Coherence@k implementation
- Counterfactual consistency tests
- Stability metrics (ARI/NMI)
- Performance benchmarks (latency)

#### Infrastructure
- Model versioning system
- Experiment tracking (wandb/MLflow)
- Performance monitoring
- Export/import functionality

### [0.3.0] - Planned

**Theme**: Advanced Features & UI

#### Features
- Web UI for visualization
- PCA/UMAP dimension comparison
- Preset saving/loading
- Demo datasets
- Web worker support for browser

#### Improvements
- Enhanced visualizations
- Interactive dimension editing
- Comparison "before/after" views
- i18n support (RU/EN)

### [0.4.0] - Planned

**Theme**: Production Ready

#### Features
- Human evaluation protocol
- Bias mitigation strategies
- Production deployment guide
- Advanced security features

#### Quality
- Comprehensive evaluation report
- Perplexity improvements
- Coherence improvements
- Security audit

#### Documentation
- Complete API documentation
- Deployment guides
- Best practices
- Case studies

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- How to report bugs
- How to suggest features
- Coding standards
- Pull request process

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: Versions before 1.0.0 are considered experimental and APIs may change.
