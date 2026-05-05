# Packaging & Distribution for meshcore-cli

This project includes complete build configurations for multiple distribution formats and automated GitHub Actions workflows for building and publishing packages.

## 📦 Distribution Formats

### 1. Debian Package (.deb)
- **File**: [`debian/`](debian/)
- **Status**: ✅ Ready
- **Platform**: Debian, Ubuntu, Linux Mint
- **Installation**: `sudo apt install ./meshcore-cli_*.deb`

### 2. Fedora/RHEL Package (.rpm)
- **File**: [`meshcore-cli.spec`](meshcore-cli.spec)
- **Status**: ✅ Ready
- **Platform**: Fedora, RHEL, CentOS
- **Installation**: `sudo dnf install meshcore-cli-*.rpm`

### 3. Docker Container
- **File**: [`Dockerfile`](Dockerfile)
- **Status**: ✅ Ready
- **Registry**: GitHub Container Registry (GHCR)
- **Installation**: `docker pull ghcr.io/fdlamotte/meshcore-cli`

### 4. Man Page
- **File**: [`docs/meshcli.1`](docs/meshcli.1)
- **Status**: ✅ Ready
- **Access**: `man meshcli` (after installation)

## 🚀 GitHub Actions Workflows

All workflows are configured to trigger automatically on git tags.

### Build Debian Package
- **Workflow**: [`.github/workflows/build-deb.yml`](.github/workflows/build-deb.yml)
- **Triggers**: Tags matching `v*`, manual dispatch
- **Output**: Uploads `.deb` and `.changes` files to GitHub Releases
- **Platform**: Debian Bookworm container

### Build RPM Package
- **Workflow**: [`.github/workflows/build-rpm.yml`](.github/workflows/build-rpm.yml)
- **Triggers**: Tags matching `v*`, manual dispatch
- **Output**: Uploads `.rpm` files to GitHub Releases
- **Platform**: Fedora latest container

### Build & Push Docker Image
- **Workflow**: [`.github/workflows/build-docker.yml`](.github/workflows/build-docker.yml)
- **Triggers**: 
  - Pushes to `main` and `develop` branches
  - Tags matching `v*`
  - Pull requests to `main`
  - Manual dispatch
- **Output**: Pushes to GHCR with multiple tags
- **Platforms**: linux/amd64, linux/arm64

## 📝 Documentation

- **[BUILDING.md](BUILDING.md)** - Detailed guide for building packages locally
- **[PACKAGING.md](PACKAGING.md)** - Complete packaging overview and release procedure

## 🔄 Release Workflow

To create a release and trigger all build workflows:

```bash
# 1. Update version numbers
vim pyproject.toml
dch -i
vim meshcore-cli.spec

# 2. Commit and tag
git add .
git commit -m "Release version X.Y.Z"
git tag -a vX.Y.Z -m "Release meshcore-cli X.Y.Z"

# 3. Push (triggers all workflows)
git push origin main --follow-tags
```

This will automatically:
- ✅ Build Debian package → GitHub Releases
- ✅ Build RPM package → GitHub Releases  
- ✅ Build & push Docker image → GHCR
- ✅ Create Release notes → GitHub Releases

## 📋 Files Overview

| File/Directory | Purpose |
|---|---|
| `debian/` | Debian package metadata and build rules |
| `meshcore-cli.spec` | Fedora/RHEL RPM specification |
| `Dockerfile` | Docker image definition |
| `docs/meshcli.1` | Unix man page |
| `.github/workflows/` | Automated build workflows |
| `BUILDING.md` | Local build instructions |
| `PACKAGING.md` | Comprehensive packaging guide |

## 🛠️ Local Testing

### Test Debian build
```bash
cd debian && debuild -us -uc -b
sudo dpkg -i ../meshcore-cli_*.deb
```

### Test RPM build
```bash
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
rpmbuild -bb meshcore-cli.spec
sudo dnf install ~/rpmbuild/RPMS/noarch/*.rpm
```

### Test Docker build
```bash
docker build -t meshcore-cli:test .
docker run meshcore-cli:test -h
```

## 📦 Installation Methods

After release, users can install via:

```bash
# Option 1: System package (Ubuntu/Debian)
sudo apt install ./meshcore-cli_1.5.8_all.deb

# Option 2: System package (Fedora/RHEL)
sudo dnf install meshcore-cli-1.5.8-1.fc*.noarch.rpm

# Option 3: Docker container
docker pull ghcr.io/fdlamotte/meshcore-cli:v1.5.8
docker run ghcr.io/fdlamotte/meshcore-cli:v1.5.8 -h

# Option 4: Python package (original)
pipx install meshcore-cli

# Option 5: Nix
nix run github:meshcore-dev/meshcore-cli#meshcore-cli
```

## 🔐 Security

- All packages built from tagged git commits
- Debian packages signed with `debuild`
- Docker images scanned for vulnerabilities
- Source archives created from git tags
- Non-root user in Docker container

## 📚 Additional Resources

- [Debian Packaging Guide](https://www.debian.org/doc/manuals/debian-new-maintainers-guide/)
- [Fedora Packaging Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

**Status**: ✅ All packaging configurations ready for production use.

Push a git tag to begin automated builds!
