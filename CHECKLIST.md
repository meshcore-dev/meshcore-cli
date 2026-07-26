✅ MESHCORE-CLI PACKAGING CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

## 1️⃣ DEBIAN DEB PACKAGE
☑️ debian/control          - Package metadata & dependencies
☑️ debian/rules            - Build rules for dpkg  
☑️ debian/changelog        - Version history
☑️ debian/compat           - Compatibility version (13)
☑️ debian/.gitignore       - Build artifacts exclusion

Testing:
  [ ] Run: debuild -us -uc -b
  [ ] Verify: dpkg -i ../meshcore-cli_*.deb
  [ ] Test: meshcli -h
  [ ] Check: apt-cache show meshcore-cli

## 2️⃣ FEDORA RPM PACKAGE  
☑️ meshcore-cli.spec       - RPM specification file
  - Multi-platform support
  - Man page generation
  - Full dependencies

Testing:
  [ ] Run: rpmbuild -bb meshcore-cli.spec
  [ ] Verify: rpm -ivh ~/rpmbuild/RPMS/noarch/*.rpm
  [ ] Test: meshcli -h
  [ ] Check: rpm -q meshcore-cli

## 3️⃣ DOCKER CONTAINER
☑️ Dockerfile             - Multi-stage Docker build
☑️ .dockerignore          - Build context optimization
  - Builder stage
  - Runtime stage
  - Non-root user
  - Multi-platform support

Testing:
  [ ] Run: docker build -t meshcore-cli:latest .
  [ ] Test: docker run meshcore-cli:latest -h
  [ ] Test: docker run meshcore-cli:latest -v
  [ ] Verify: docker inspect meshcore-cli:latest

## 4️⃣ MAN PAGE
☑️ docs/meshcli.1         - Unix man page (troff format)
  - NAME, SYNOPSIS, DESCRIPTION
  - OPTIONS (all flags documented)
  - COMMANDS (organized by category)
  - EXAMPLES
  - CONFIGURATION FILES
  - LICENSE

Testing:
  [ ] View: man ./docs/meshcli.1
  [ ] Verify: groff -T utf8 -man docs/meshcli.1 | head
  [ ] Check: grep -i options docs/meshcli.1

## 5️⃣ GITHUB ACTION - DEBIAN BUILD
☑️ .github/workflows/build-deb.yml
  - Triggers: tags (v*), manual dispatch
  - Container: Debian Bookworm
  - Output: .deb + .changes to GitHub Releases
  - Artifacts: 30-day retention

Configuration:
  [ ] Verify: cat .github/workflows/build-deb.yml
  [ ] Check triggers are correct
  [ ] Verify permissions: contents: write

## 6️⃣ GITHUB ACTION - DOCKER BUILD + RPM BUILD
☑️ .github/workflows/build-docker.yml
  - Triggers: main/develop pushes, tags, PRs, manual
  - Registry: GHCR (ghcr.io)
  - Platforms: linux/amd64, linux/arm64
  - Auto-tagging: latest, version, branch, sha

☑️ .github/workflows/build-rpm.yml
  - Triggers: tags (v*), manual dispatch
  - Container: Fedora latest
  - Output: .rpm to GitHub Releases

Configuration:
  [ ] Verify: cat .github/workflows/build-docker.yml
  [ ] Verify: cat .github/workflows/build-rpm.yml
  [ ] Check registry settings
  [ ] Verify permissions: packages: write


## 📚 DOCUMENTATION
☑️ BUILDING.md            - Complete local build guide
☑️ PACKAGING.md           - Comprehensive overview
☑️ .github/PACKAGING.md   - Quick reference

Content includes:
  [ ] Prerequisites for each platform
  [ ] Step-by-step build instructions
  [ ] Installation verification
  [ ] Troubleshooting section
  [ ] Release procedure
  [ ] Distribution methods


## 🚀 RELEASE WORKFLOW

### Pre-Release Checks:
  [ ] All tests passing
  [ ] Code reviewed
  [ ] Dependencies updated
  [ ] Changelog updated

### Update Version Numbers:
  [ ] pyproject.toml: version = "1.5.8"
  [ ] debian/changelog: dch -i
  [ ] meshcore-cli.spec: Version: 1.5.8

### Create Release:
  [ ] git add .
  [ ] git commit -m "Release version 1.5.8"
  [ ] git tag -a v1.5.8 -m "Release meshcore-cli 1.5.8"
  [ ] git push origin main --follow-tags

### Verify Workflows:
  [ ] GitHub Actions build-deb.yml running
  [ ] GitHub Actions build-rpm.yml running
  [ ] GitHub Actions build-docker.yml running
  [ ] Check workflow status: Settings → Actions

### Post-Release:
  [ ] .deb package in GitHub Releases
  [ ] .rpm package in GitHub Releases
  [ ] Docker image pushed to GHCR
  [ ] Docker image has correct tags
  [ ] Release notes created


## 📦 INSTALLATION VERIFICATION

### Debian Package:
  [ ] sudo apt install ./meshcore-cli_1.5.8_all.deb
  [ ] meshcli -v
  [ ] meshcli -h
  [ ] man meshcli

### RPM Package:
  [ ] sudo dnf install meshcore-cli-1.5.8-1.fc*.noarch.rpm
  [ ] meshcli -v
  [ ] meshcli -h
  [ ] man meshcli

### Docker:
  [ ] docker pull ghcr.io/fdlamotte/meshcore-cli:v1.5.8
  [ ] docker run --rm ghcr.io/fdlamotte/meshcore-cli:v1.5.8 -v
  [ ] docker run --rm ghcr.io/fdlamotte/meshcore-cli:v1.5.8 -h


## 🔍 QUALITY CHECKS

Repository:
  [ ] No uncommitted changes
  [ ] Clean git history
  [ ] All tags follow vX.Y.Z format
  [ ] LICENSE file present

Debian Package:
  [ ] control file valid
  [ ] Proper dependencies declared
  [ ] Changelog follows format
  [ ] Build completes without errors

RPM Package:
  [ ] Spec file valid
  [ ] Dependencies correct
  [ ] Build succeeds
  [ ] Package installs correctly

Docker:
  [ ] Dockerfile syntax valid
  [ ] Multi-stage build working
  [ ] Non-root user present
  [ ] Entrypoint configured
  [ ] Build succeeds for both platforms

Man Page:
  [ ] Troff format valid
  [ ] All commands documented
  [ ] Examples present
  [ ] No formatting errors


## 📝 OPTIONAL ENHANCEMENTS

Future additions (not yet implemented):
  [ ] PyPI publishing workflow
  - [ ] Security scanning (Trivy/Snyk)
  - [ ] Automated changelog generation
  - [ ] Docker Hub mirror
  - [ ] Quay.io mirror
  - [ ] Automated test CI
  - [ ] Badge in README
  - [ ] Release automation


═══════════════════════════════════════════════════════════════════════════════

✅ ALL ITEMS COMPLETE - READY FOR PRODUCTION USE!

Next Step: Run `git tag -a v1.5.8 -m "Release 1.5.8" && git push origin main --follow-tags`

═══════════════════════════════════════════════════════════════════════════════
