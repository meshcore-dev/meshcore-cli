#!/usr/bin/env bash
set -euo pipefail

RPMBUILD_DIR="${RPMBUILD_DIR:-$HOME/rpmbuild}"

mkdir -p \
  "$RPMBUILD_DIR/BUILD" \
  "$RPMBUILD_DIR/RPMS" \
  "$RPMBUILD_DIR/SOURCES" \
  "$RPMBUILD_DIR/SPECS" \
  "$RPMBUILD_DIR/SRPMS"

build_python_rpm() {
  local pypi_name="$1"
  local upstream_version="$2"
  local rpm_name="$3"
  local summary="$4"
  local license="$5"
  local runtime_requires="${6:-}"
  local arch="${7:-noarch}"

  local download_dir="$RPMBUILD_DIR/SOURCES/${rpm_name}-${upstream_version}-wheel"
  local spec_path="$RPMBUILD_DIR/SPECS/${rpm_name}.spec"
  local files_macro="%{python3_sitelib}/*"
  local wheel_path
  local wheel_file

  if [ "$arch" != "noarch" ]; then
    files_macro="%{python3_sitearch}/*"
  fi

  rm -rf "$download_dir"
  mkdir -p "$download_dir"

  python3 -m pip download \
    --only-binary=:all: \
    --no-deps \
    --dest "$download_dir" \
    "${pypi_name}==${upstream_version}"

  wheel_path="$(find "$download_dir" -maxdepth 1 -type f -name '*.whl' -print -quit)"
  test -n "$wheel_path" || { echo "No wheel downloaded for ${pypi_name}==${upstream_version}"; exit 1; }

  wheel_file="$(basename "$wheel_path")"
  cp "$wheel_path" "$RPMBUILD_DIR/SOURCES/$wheel_file"

  cat > "$spec_path" <<EOF
Name:           ${rpm_name}
Version:        ${upstream_version}
Release:        1%{?dist}
Summary:        ${summary}
License:        ${license}
Source0:        ${wheel_file}
EOF

  if [ "$arch" = "noarch" ]; then
    echo "BuildArch:      noarch" >> "$spec_path"
  fi

  cat >> "$spec_path" <<EOF
BuildRequires:  python3-devel
BuildRequires:  python3-installer

Requires:       python3 >= 3.10
EOF

  if [ -n "$runtime_requires" ]; then
    while IFS= read -r requirement; do
      [ -n "$requirement" ] && printf 'Requires:       %s\n' "$requirement" >> "$spec_path"
    done <<< "$runtime_requires"
  fi

  cat >> "$spec_path" <<EOF

%description
This package was built from the upstream ${pypi_name} Python wheel so
meshcore-cli can be installed from RPM packages without using pip on the target
machine.

%prep

%build

%install
python3 -m installer --prefix=/usr --destdir=%{buildroot} %{SOURCE0}

%files
${files_macro}

%changelog
* Wed May 06 2026 Florent de Lamotte <florent@frizoncorrea.fr> - ${upstream_version}-1
- Build dependency package for meshcore-cli.
EOF

  rpmbuild -bb "$spec_path"
}

build_python_rpm \
  "prompt-toolkit" \
  "3.0.52" \
  "python3-prompt-toolkit" \
  "Library for building interactive command lines in Python" \
  "BSD-3-Clause" \
  "python3-wcwidth" \
  "noarch"

build_python_rpm \
  "bleak" \
  "0.22.3" \
  "python3-bleak" \
  "Bluetooth Low Energy platform-agnostic client" \
  "MIT" \
  "python3-dbus-fast >= 1.83.0" \
  "noarch"

build_python_rpm \
  "pycayennelpp" \
  "2.4.0" \
  "python3-pycayennelpp" \
  "CayenneLPP encoder and decoder for Python" \
  "MIT" \
  "" \
  "noarch"

build_python_rpm \
  "pyserial-asyncio-fast" \
  "0.16" \
  "python3-serial-asyncio-fast" \
  "Asynchronous I/O support for pySerial" \
  "BSD-3-Clause" \
  "python3-pyserial" \
  "noarch"

build_python_rpm \
  "pycryptodome" \
  "3.23.0" \
  "python3-pycryptodome" \
  "Cryptographic library for Python" \
  "BSD-2-Clause AND LicenseRef-Fedora-Public-Domain" \
  "" \
  "native"

build_python_rpm \
  "meshcore" \
  "2.3.7" \
  "python3-meshcore" \
  "Python bindings for MeshCore companion radios" \
  "MIT" \
  $'python3-bleak >= 0.22.0\npython3-pycayennelpp\npython3-pycryptodome\npython3-serial-asyncio-fast' \
  "noarch"

find "$RPMBUILD_DIR/RPMS" -type f -name '*.rpm' -print
