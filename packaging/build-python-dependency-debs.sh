#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$ROOT_DIR/build/debian-python-deps"
OUTPUT_DIR="$ROOT_DIR/dist/debian"

mkdir -p "$WORK_DIR" "$OUTPUT_DIR"

build_python_deb() {
  local pypi_name="$1"
  local upstream_version="$2"
  local source_name="$3"
  local package_name="$4"
  local summary="$5"
  local runtime_depends="${6:-}"

  local package_dir="$WORK_DIR/${source_name}-${upstream_version}"
  local depends="\${misc:Depends}, python3 (>= 3.10)"
  if [ -n "$runtime_depends" ]; then
    depends="$depends, $runtime_depends"
  fi

  rm -rf "$package_dir"
  mkdir -p "$package_dir/debian/source" "$package_dir/wheels"

  python3 -m pip download \
    --only-binary=:all: \
    --no-deps \
    --dest "$package_dir/wheels" \
    "${pypi_name}==${upstream_version}"

  cat > "$package_dir/debian/control" <<EOF
Source: ${source_name}
Maintainer: Florent de Lamotte <florent@frizoncorrea.fr>
Section: python
Priority: optional
Standards-Version: 4.6.2
Build-Depends: debhelper-compat (= 13),
               dh-python,
               python3-installer

Package: ${package_name}
Architecture: all
Depends: ${depends}
Description: ${summary}
 This package was built from the upstream ${pypi_name} Python wheel so
 meshcore-cli can be installed from Debian packages without using pip on
 the target machine.
EOF

  cat > "$package_dir/debian/changelog" <<EOF
${source_name} (${upstream_version}) unstable; urgency=medium

  * Build dependency package for meshcore-cli.

 -- Florent de Lamotte <florent@frizoncorrea.fr>  Wed, 06 May 2026 00:00:00 +0000
EOF

  cat > "$package_dir/debian/rules" <<EOF
#!/usr/bin/make -f

%:
	dh \$@ --with python3

override_dh_auto_build:

override_dh_auto_test:

override_dh_auto_install:
	python3 -m installer --prefix=/usr --destdir=debian/${package_name} wheels/*.whl
EOF

  chmod +x "$package_dir/debian/rules"
  echo "3.0 (native)" > "$package_dir/debian/source/format"

  (cd "$package_dir" && dpkg-buildpackage -us -uc -b)

  find "$WORK_DIR" -maxdepth 1 -type f \
    \( -name "${package_name}_*.deb" -o -name "${source_name}_*.changes" \) \
    -exec cp {} "$OUTPUT_DIR/" \;
}

build_python_deb \
  "typing-extensions" \
  "4.13.2" \
  "typing-extensions" \
  "python3-typing-extensions" \
  "Backported and experimental type hints for Python" \
  ""

build_python_deb \
  "prompt-toolkit" \
  "3.0.52" \
  "prompt-toolkit" \
  "python3-prompt-toolkit" \
  "Library for building interactive command lines in Python" \
  "python3-wcwidth"

build_python_deb \
  "bleak" \
  "0.22.3" \
  "bleak" \
  "python3-bleak" \
  "Bluetooth Low Energy platform-agnostic client" \
  "python3-dbus-fast (>= 1.83.0), python3-typing-extensions (>= 4.7.0)"

build_python_deb \
  "pycayennelpp" \
  "2.4.0" \
  "pycayennelpp" \
  "python3-pycayennelpp" \
  "CayenneLPP encoder and decoder for Python" \
  ""

build_python_deb \
  "pyserial-asyncio-fast" \
  "0.16" \
  "pyserial-asyncio-fast" \
  "python3-serial-asyncio-fast" \
  "Asynchronous I/O support for pySerial" \
  "python3-serial"

build_python_deb \
  "meshcore" \
  "2.3.7" \
  "meshcore" \
  "python3-meshcore" \
  "Python bindings for MeshCore companion radios" \
  "python3-bleak (>= 0.22.0), python3-pycayennelpp, python3-pycryptodome, python3-serial-asyncio-fast"

ls -l "$OUTPUT_DIR"
