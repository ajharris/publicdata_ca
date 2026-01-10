# Publishing to PyPI

This document describes how to publish publicdata-ca to PyPI.

## Prerequisites

1. Install build tools:
   ```bash
   pip install --upgrade build twine
   ```

2. Create accounts:
   - [PyPI](https://pypi.org/account/register/)
   - [TestPyPI](https://test.pypi.org/account/register/) (for testing)

3. Configure credentials in `~/.pypirc`:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-...

   [testpypi]
   username = __token__
   password = pypi-...
   ```

## Pre-Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Run full test suite: `pytest`
- [ ] Verify package metadata: `python -m build --check`
- [ ] Test installation locally: `pip install -e .`
- [ ] Review README.md renders correctly on GitHub
- [ ] Tag release in git: `git tag v0.1.0`

## Build Distribution

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python -m build

# Verify contents
tar -tzf dist/publicdata-ca-*.tar.gz | head -20
unzip -l dist/publicdata_ca-*.whl | head -20
```

## Test on TestPyPI

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    publicdata-ca

# Verify it works
python -c "from publicdata_ca import __version__; print(__version__)"
publicdata --version
```

## Publish to PyPI

```bash
# Upload to PyPI (production)
python -m twine upload dist/*

# Test installation from PyPI
pip install publicdata-ca

# Verify it works
python -c "from publicdata_ca import __version__; print(__version__)"
publicdata --version
```

## Post-Release

- [ ] Push git tag: `git push --tags`
- [ ] Create GitHub release with changelog
- [ ] Update documentation links if needed
- [ ] Announce release (Twitter, Reddit, etc.)

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backwards compatible)
- **PATCH** version for bug fixes (backwards compatible)

Examples:
- `0.1.0` - Initial alpha release
- `0.2.0` - Added new provider
- `0.2.1` - Fixed bug in CMHC resolver
- `1.0.0` - First stable release

## Troubleshooting

### "File already exists" error

PyPI doesn't allow re-uploading the same version. You must:
1. Increment the version number in `pyproject.toml`
2. Rebuild: `python -m build`
3. Upload again: `python -m twine upload dist/*`

### README not rendering

- Ensure `readme = "README.md"` in `pyproject.toml`
- Verify README.md is valid Markdown
- Check for unsupported features (PyPI uses a subset of Markdown)

### Missing dependencies

- Ensure all dependencies are listed in `dependencies` in `pyproject.toml`
- Don't rely on system packages or conda environments

### Import errors after installation

- Check `[tool.setuptools.packages.find]` includes all packages
- Verify package structure with `python -m build --check`

## Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [TestPyPI](https://test.pypi.org/)
- [Twine Documentation](https://twine.readthedocs.io/)
