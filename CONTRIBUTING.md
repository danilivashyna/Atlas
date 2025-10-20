# Contributing to Atlas

Thank you for your interest in contributing to Atlas - Semantic Space Control Panel! This document provides guidelines and information for contributors.

## 🎯 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of semantic spaces and NLP

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Atlas.git
   cd Atlas
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -e .[dev]
   ```

4. **Run Tests**
   ```bash
   pytest tests/
   ```

## 📝 Code Style

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

- **Line length**: Maximum 100 characters (soft limit 88 for Black compatibility)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings, single quotes for dict keys when possible
- **Imports**: Organized in three groups (stdlib, third-party, local)

### Formatting Tools

We use:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking (gradually being added)

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `SemanticSpace`)
- **Functions/methods**: `snake_case` (e.g., `encode_text`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_DIMENSION`)
- **Private members**: `_leading_underscore` (e.g., `_internal_method`)

## 🌿 Branching Strategy

### Branch Naming

Use descriptive branch names with prefixes:

- `feature/` - New features (e.g., `feature/add-api-endpoint`)
- `fix/` - Bug fixes (e.g., `fix/decoder-reasoning`)
- `docs/` - Documentation updates (e.g., `docs/update-readme`)
- `test/` - Test additions/improvements (e.g., `test/add-decoder-tests`)
- `refactor/` - Code refactoring (e.g., `refactor/simplify-encoder`)

### Workflow

1. **Create a branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** with clear, focused commits

3. **Keep your branch updated**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

4. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

## ✅ Pull Request Checklist

Before submitting a PR, ensure:

### Code Quality
- [ ] Code follows PEP 8 style guidelines
- [ ] All new code has appropriate docstrings
- [ ] Type hints are added where applicable
- [ ] No unnecessary comments (code should be self-documenting)
- [ ] No print statements (use logging instead)

### Testing
- [ ] All existing tests pass: `pytest tests/`
- [ ] New tests added for new functionality
- [ ] Test coverage maintained or improved
- [ ] Edge cases are tested
- [ ] Integration tests added if applicable

### Documentation
- [ ] README.md updated if user-facing changes
- [ ] DOCUMENTATION.md updated if API changes
- [ ] Docstrings added/updated for new/modified functions
- [ ] Examples updated if behavior changes
- [ ] CHANGELOG.md updated (if applicable)

### Performance
- [ ] No significant performance regressions
- [ ] Large files not committed (use .gitignore)
- [ ] No hardcoded paths or credentials

### Git
- [ ] Commits are atomic and well-described
- [ ] Commit messages follow convention (see below)
- [ ] Branch is up to date with main
- [ ] No merge commits (use rebase)

## 📋 Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions or modifications
- `chore`: Build process or auxiliary tool changes
- `ci`: CI/CD changes

### Examples

```
feat(encoder): add batch encoding support

Implement batch encoding to process multiple texts efficiently.
This reduces API latency by 40% for bulk operations.

Closes #123
```

```
fix(decoder): handle empty vector input

Add validation to prevent crashes when decoding empty vectors.
Returns appropriate error message instead.

Fixes #456
```

```
docs(readme): update installation instructions

Clarify Python version requirements and add troubleshooting section.
```

## 🧪 Testing Guidelines

### Test Organization

- `tests/test_<module>.py` - Unit tests for each module
- `tests/integration/` - Integration tests
- `tests/fixtures/` - Shared test fixtures and data
- `tests/golden/` - Golden sample tests (regression)

### Writing Tests

1. **One test per behavior**
   ```python
   def test_encode_returns_correct_shape():
       """Test that encoder returns 5D vector"""
       encoder = SimpleSemanticEncoder()
       vector = encoder.encode_text("test")
       assert vector.shape == (5,)
   ```

2. **Use descriptive names**
   - Good: `test_decoder_handles_zero_vector`
   - Bad: `test_decoder_1`

3. **Test edge cases**
   - Empty inputs
   - Boundary values (±1 for normalized vectors)
   - Invalid inputs
   - Large inputs

4. **Use fixtures for common setup**
   ```python
   @pytest.fixture
   def semantic_space():
       return SemanticSpace()
   ```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_encoder.py

# Run with coverage
pytest --cov=atlas tests/

# Run specific test
pytest tests/test_encoder.py::test_encode_single_text

# Run with verbose output
pytest -v tests/
```

## 📚 Documentation Guidelines

### Docstring Format

We use Google-style docstrings:

```python
def encode_text(self, text: Union[str, List[str]]) -> np.ndarray:
    """
    Encode text into 5D semantic space.

    This method compresses text into a 5-dimensional vector where each
    dimension represents a distinct semantic property.

    Args:
        text: Input text or list of texts to encode

    Returns:
        5D semantic vector(s). If input is a string, returns (5,) array.
        If input is a list, returns (n, 5) array.

    Raises:
        ValueError: If text is empty or None

    Examples:
        >>> encoder = SimpleSemanticEncoder()
        >>> vector = encoder.encode_text("Собака")
        >>> vector.shape
        (5,)
    """
```

### Module Docstrings

Each module should start with a docstring:

```python
"""
Semantic Encoder - Compresses text into 5-dimensional semantic space

This module provides encoding functionality to transform text into
interpretable 5D vectors where each dimension captures a distinct
semantic property.
"""
```

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing [issues](https://github.com/danilivashyna/Atlas/issues)
2. Verify bug exists in latest version
3. Collect reproduction steps

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. ...
2. ...

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.9.7]
- Atlas version: [e.g., 0.1.0]
- Dependencies: [run `pip freeze`]

**Additional Context**
Any other relevant information
```

## 💡 Suggesting Features

### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature

**Motivation**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How should it work?

**Alternatives Considered**
Other approaches you've thought about

**Additional Context**
Examples, mockups, or related issues
```

## 🔍 Code Review Process

### For Contributors

1. **Keep PRs focused** - One feature/fix per PR
2. **Respond to feedback** - Address reviewer comments promptly
3. **Be patient** - Reviews take time
4. **Be open** - Accept constructive criticism

### For Reviewers

1. **Be respectful** - Critique code, not people
2. **Be specific** - Provide actionable feedback
3. **Be timely** - Review within a few days
4. **Approve when ready** - Don't nitpick minor issues

## 🏆 Recognition

Contributors are recognized in:
- [Contributors section](https://github.com/danilivashyna/Atlas/graphs/contributors) on GitHub
- Release notes for significant contributions
- README.md for major features

## 📞 Getting Help

- **Questions**: Open a [Discussion](https://github.com/danilivashyna/Atlas/discussions)
- **Bugs**: Open an [Issue](https://github.com/danilivashyna/Atlas/issues)
- **Security**: See [SECURITY.md](SECURITY.md)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Atlas! 🗺️✨
