# meshcore-cli Build Pipeline Summary

## ✅ Completed Steps

All six steps for building Debian, Fedora, Docker, and GitHub Actions workflows have been successfully implemented!

### Step 1: Debian DEB Package ✓

**Files created in `debian/` directory:**
- `debian/control` - Package metadata, dependencies, and description
- `debian/rules` - Build rules for the package
- `debian/changelog` - Version history
- `debian/compat` - Compatibility version (13)
- `debian/.gitignore` - Git ignore patterns for build artifacts

**Key features:**
- Targets Debian/Ubuntu
- Builds release `.deb` packages for meshcore-cli and missing Python dependencies
- Uses Python 3.10+ requirement
- Includes comprehensive package description

**Build locally:**
```bash
debuild -us -uc -b
# Or
dpkg-buildpackage -us -uc -b
```

---

### Step 2: Fedora RPM Package ✓

**File created:**
- `meshcore-cli.spec` - RPM specification file

**Key features:**
- Targets Fedora/RHEL
- Includes all runtime dependencies
- Multi-stage build support
- Man page generation included
- License: MIT

**Build locally:**
```bash
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
cp meshcore-cli.spec ~/rpmbuild/SPECS/
git archive --prefix=meshcore-cli-1.5.7/ --format=tar.gz \
  -o ~/rpmbuild/SOURCES/meshcore-cli-1.5.7.tar.gz HEAD
rpmbuild -bb ~/rpmbuild/SPECS/meshcore-cli.spec
```

---

### Step 3: Docker Container ✓

**File created:**
- `Dockerfile` - Multi-stage Docker build

**Key features:**
- Multi-stage build for smaller image size
- Builder stage: Compiles the package
- Runtime stage: Lightweight Python 3.10 base
- Non-root user (meshcore) with UID 1000
- Proper entrypoint: `meshcli` command
- Support for all connection types (BLE, TCP, Serial)
- Includes necessary system libraries (dbus, glib2)

**Build locally:**
```bash
docker build -t meshcore-cli:latest .
```

**Run the container:**
```bash
docker run --rm meshcore-cli:latest -h
docker run --rm meshcore-cli:latest -v
docker run -it --device=/dev/ttyUSB0 meshcore-cli:latest chat
```

---

### Step 4: Man Page ✓

**File created:**
- `docs/meshcli.1` - Complete man page (troff format)

**Sections included:**
- NAME - Brief description
- SYNOPSIS - Usage syntax
- DESCRIPTION - Detailed explanation
- OPTIONS - All command-line flags with descriptions
- COMMANDS - All available commands organized by category
- CONFIGURATION FILES - Config file locations and purposes
- OUTPUT MODES - JSON and text output explanation
- EXAMPLES - Real-world usage examples
- AUTHOR - Maintainer information
- LICENSE - MIT License reference

**Access the man page:**
```bash
man ./docs/meshcli.1
```

---

### Step 5: GitHub Action for Debian Build ✓

**File created:**
- `.github/workflows/build-deb.yml`

**Workflow features:**
- Triggers on: Git tags (v*) and manual dispatch
- Runs on: Debian Bookworm container
- Installs all build dependencies automatically
- Builds separate `.deb` packages for meshcore-cli Python dependencies
- Builds .deb package using debuild
- Uploads artifacts to workflow (30-day retention)
- Creates GitHub Release with all .deb and .changes files
- Permissions: Write access to contents

**Triggered by:**
```bash
git tag -a v1.5.8 -m "Release 1.5.8"
git push origin v1.5.8
```

---

### Step 6: GitHub Action for Docker Build ✓

**File created:**
- `.github/workflows/build-docker.yml`

**Workflow features:**
- Triggers on:
  - Pushes to `main` and `develop` branches
  - Git tags (v*)
  - Pull requests to `main`
  - Manual dispatch
- Uses Docker buildx for multi-platform builds
- Supports: linux/amd64 and linux/arm64
- Pushes to GitHub Container Registry (GHCR)
- Cache optimization enabled
- Automatic tagging strategy:
  - `latest` (for main branch)
  - `<branch-name>` (for branch pushes)
  - `<version>` (for semantic version tags)
  - `<short-sha>` (for commit references)

**Registry:** `ghcr.io/<owner>/meshcore-cli`

**Pull image:**
```bash
docker pull ghcr.io/fdlamotte/meshcore-cli:latest
docker pull ghcr.io/fdlamotte/meshcore-cli:v1.5.8
```

---

## Additional Files

### Supporting Files Created:

1. **`.dockerignore`** - Excludes unnecessary files from Docker build context
2. **`BUILDING.md`** - Comprehensive guide for building locally
   - Detailed prerequisites for each platform
   - Step-by-step build instructions
   - Installation verification steps
   - Troubleshooting section
   - Release procedure

---

## Directory Structure

```
meshcore-cli/
├── debian/                           # Debian packaging
│   ├── control                       # Package metadata
│   ├── rules                         # Build rules
│   ├── changelog                     # Version history
│   ├── compat                        # Compatibility version
│   └── .gitignore
├── docs/
│   └── meshcli.1                     # Man page
├── .github/workflows/
│   ├── build-deb.yml                 # Debian build workflow
│   ├── build-rpm.yml                 # RPM build workflow
│   └── build-docker.yml              # Docker build workflow
├── meshcore-cli.spec                 # Fedora RPM spec
├── Dockerfile                        # Docker image definition
├── .dockerignore                     # Docker build exclusions
└── BUILDING.md                       # Build documentation
```

---

## Quick Start for Creating a Release

### 1. Update versions:

```bash
# Update pyproject.toml
sed -i 's/version = "1.5.7"/version = "1.5.8"/' pyproject.toml

# Update debian/changelog
dch -i -v 1.5.8-1 -D unstable "Release 1.5.8"

# Update meshcore-cli.spec
sed -i 's/Version:        1.5.7/Version:        1.5.8/' meshcore-cli.spec
```

### 2. Commit and tag:

```bash
git add .
git commit -m "Release version 1.5.8"
git tag -a v1.5.8 -m "Release meshcore-cli 1.5.8"
git push origin main --follow-tags
```

### 3. Workflows automatically trigger:
- ✅ Debian .deb package set built and uploaded to Releases
- ✅ Fedora .rpm package built and uploaded to Releases
- ✅ Docker image built and pushed to GHCR

### 4. Verify releases:

```bash
# Check GitHub Releases page for .deb package set and .rpm
# Docker image available at:
docker pull ghcr.io/fdlamotte/meshcore-cli:v1.5.8
```

---

## Distribution Methods

Users can now install meshcore-cli via:

1. **Debian/Ubuntu**: download all Debian `.deb` assets, then run `sudo apt install ./*.deb`
2. **Fedora/RHEL**: download all RPM assets, then run `sudo dnf install ./*.rpm`
3. **Docker**: `docker pull ghcr.io/fdlamotte/meshcore-cli:v1.5.8`
4. **pipx** (original): `pipx install meshcore-cli`
5. **Nix**: `nix run github:meshcore-dev/meshcore-cli#meshcore-cli`

---

## Next Steps (Optional Enhancements)

1. **PyPI Publishing**: Add `publish-to-pypi.yml` workflow
2. **Security Scanning**: Add Trivy or Snyk for vulnerability scanning
3. **Automated Testing**: Add CI workflow for running tests on push
4. **Changelog Auto-generation**: Add release notes automation
5. **Container Registry Alternatives**: Support Docker Hub, Quay.io, etc.

---

## References

- Debian Packaging: [debian/](./debian/)
- RPM Packaging: [meshcore-cli.spec](./meshcore-cli.spec)
- Docker: [Dockerfile](./Dockerfile)
- Documentation: [BUILDING.md](./BUILDING.md)
- Man Page: [docs/meshcli.1](./docs/meshcli.1)
- GitHub Actions: [.github/workflows/](./.github/workflows/)

All configurations are ready to use. Simply push a git tag to trigger the build pipelines!
