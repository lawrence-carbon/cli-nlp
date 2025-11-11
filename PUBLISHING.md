# Publishing Guide

This document explains how to publish `cli-nlp` to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/
2. **API Token**: Generate an API token at https://pypi.org/manage/account/token/
   - Go to Account Settings → API tokens
   - Create a new token with "Entire account" scope (or project-specific scope)
   - Copy the token (you won't be able to see it again!)

## Setting up GitHub Secrets

1. Go to your repository: https://github.com/lawrence-carbon/cli-nlp
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `PYPI_API_TOKEN`
5. Value: Paste your PyPI API token
6. Click **Add secret**

## Publishing a New Version

### Method 1: Using GitHub Releases (Recommended)

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.1.1"  # Increment as needed
   ```

2. **Commit and push** the version change:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.1.1"
   git push
   ```

3. **Create a GitHub Release**:
   - Go to https://github.com/lawrence-carbon/cli-nlp/releases/new
   - Click "Choose a tag" and create a new tag (e.g., `v0.1.1`)
   - Fill in release title and description
   - Click "Publish release"

4. **GitHub Actions will automatically**:
   - Build the package
   - Publish to PyPI
   - You can monitor progress in the Actions tab

### Method 2: Manual Trigger

1. **Update version** in `pyproject.toml`
2. **Commit and push** the changes
3. Go to **Actions** tab in GitHub
4. Select **Build and Publish to PyPI** workflow
5. Click **Run workflow** → **Run workflow**

### Method 3: Local Publishing (for testing)

```bash
# Build the package
poetry build

# Test installation locally
pip install dist/cli_nlp-*.whl

# Publish to PyPI (requires PYPI_API_TOKEN)
poetry config pypi-token.pypi "your-token-here"
poetry publish
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes, backward compatible

## Verifying Publication

After publishing, verify the package is available:

```bash
pip install cli-nlp
nlp --help
```

Check PyPI: https://pypi.org/project/cli-nlp/

## Troubleshooting

### Workflow fails with "PYPI_API_TOKEN not set"
- Ensure the secret is set in GitHub repository settings
- Check that the secret name matches exactly: `PYPI_API_TOKEN`

### Package already exists error
- Increment the version number in `pyproject.toml`
- Commit and try again

### Build fails
- Check that `poetry.lock` is committed
- Ensure all dependencies are properly specified in `pyproject.toml`

