# Building and Packaging meshcore-cli

This document describes how to build meshcore-cli as a Debian package, Fedora RPM, and Docker container.

## Prerequisites

### For all builds
- Git
- Python 3.10+

### For Debian (.deb) package
```bash
sudo apt-get install -y build-essential debhelper-compat devscripts fakeroot python3-all python3-hatchling python3-setuptools
```

### For Fedora (.rpm) package
```bash
sudo dnf install -y rpm-build python3-devel python3-pip help2man
```

### For Docker
- Docker or Podman installed and running

## Building Debian Package

### Method 1: Using debuild (Recommended for Debian/Ubuntu)

```bash
cd /path/to/meshcore-cli
debuild -us -uc -b
```

This creates:
- `../meshcore-cli_*.deb` - the binary package
- `../meshcore-cli_*.changes` - the package changes file

### Method 2: Using dpkg-buildpackage

```bash
cd /path/to/meshcore-cli
dpkg-buildpackage -us -uc -b
```

### Install the built package

```bash
sudo dpkg -i ../meshcore-cli_*.deb
sudo apt-get install -f  # Install any missing dependencies
```

### Test the installation

```bash
meshcli -h
meshcli -v
```

## Building Fedora RPM Package

### Prerequisites

```bash
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
```

### Build the package

```bash
cd /path/to/meshcore-cli

# Copy spec file
cp meshcore-cli.spec ~/rpmbuild/SPECS/

# Create source tarball (replace VERSION with actual version, e.g., 1.5.7)
git archive --prefix=meshcore-cli-1.5.7/ --format=tar.gz \
  -o ~/rpmbuild/SOURCES/meshcore-cli-1.5.7.tar.gz HEAD

# Build RPM
rpmbuild -bb ~/rpmbuild/SPECS/meshcore-cli.spec
```

### Install the built package

```bash
sudo dnf install ~/rpmbuild/RPMS/*/*.rpm
```

### Test the installation

```bash
meshcli -h
meshcli -v
```

## Building Docker Container

### Build the image

```bash
cd /path/to/meshcore-cli
docker build -t meshcore-cli:latest .
```

### Build with specific version tag

```bash
docker build -t meshcore-cli:1.5.7 .
```

### Run the container

```bash
# Display help
docker run --rm meshcore-cli:latest -h

# Display version
docker run --rm meshcore-cli:latest -v

# Interactive mode (requires proper BLE/Serial setup)
docker run --rm -it --device=/dev/ttyUSB0 meshcore-cli:latest chat
```

### Build for multiple platforms

Using buildx (requires Docker buildx):

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t meshcore-cli:latest .
```

## GitHub Actions Workflows

### Debian Package Workflow (.github/workflows/build-deb.yml)

Triggers on:
- Git tags matching `v*` pattern (e.g., `v1.5.7`)
- Manual workflow dispatch

Builds and uploads Debian package to GitHub Releases.

### RPM Package Workflow (.github/workflows/build-rpm.yml)

Triggers on:
- Git tags matching `v*` pattern
- Manual workflow dispatch

Builds and uploads the RPM package set to GitHub Releases.

### Docker Workflow (.github/workflows/build-docker.yml)

Triggers on:
- Pushes to `main` and `develop` branches
- Tags matching `v*` pattern
- Pull requests to `main`
- Manual workflow dispatch

Builds and pushes Docker image to GitHub Container Registry (GHCR).

Tags generated:
- `latest` (for default branch)
- `<branch-name>` (for branch pushes)
- `<version>` (for version tags)
- `<sha>` (for commit sha)

## Creating a Release

### 1. Update version in pyproject.toml
```toml
version = "1.5.8"
```

### 2. Update Debian changelog
```bash
dch -i -v 1.5.8-1 -D unstable "Release 1.5.8"
```

### 3. Update meshcore-cli.spec
```spec
Version:        1.5.8
Release:        1%{?dist}
```

### 4. Commit and tag
```bash
git add .
git commit -m "Release version 1.5.8"
git tag -a v1.5.8 -m "Release meshcore-cli 1.5.8"
git push origin main
git push origin v1.5.8
```

This will trigger all three workflows:
- Debian package build and upload
- RPM package build and upload
- Docker image build and push to GHCR

## Distribution

### Install from .deb package
```bash
sudo dpkg -i meshcore-cli_1.5.8_all.deb
```

### Install from .rpm package
```bash
sudo dnf install ./*.rpm
```

### Pull from Docker Registry
```bash
docker pull ghcr.io/fdlamotte/meshcore-cli:v1.5.8
docker run ghcr.io/fdlamotte/meshcore-cli:v1.5.8 -h
```

### Install via pipx (original method)
```bash
pipx install meshcore-cli
```

## Troubleshooting

### Debian build fails with "debuild command not found"
```bash
sudo apt-get install devscripts
```

### RPM build fails with "rpmbuild command not found"
```bash
sudo dnf install rpm-build
```

### Docker build fails with "permission denied"
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Then logout and login
```

### Man page not generating in RPM build
Install help2man:
```bash
sudo dnf install help2man
```

## File Structure

```
meshcore-cli/
├── debian/                    # Debian package files
│   ├── control
│   ├── rules
│   ├── changelog
│   ├── compat
│   └── .gitignore
├── meshcore-cli.spec         # Fedora RPM spec file
├── Dockerfile                # Docker build file
├── docs/
│   └── meshcli.1            # Man page
└── .github/workflows/
    ├── build-deb.yml         # Debian build action
    ├── build-rpm.yml         # RPM build action
    └── build-docker.yml      # Docker build action
```

## References

- [Debian Packaging Guide](https://www.debian.org/doc/manuals/debian-faq/ch-pkg_basics.en.html)
- [Fedora Packaging Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/)
- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
