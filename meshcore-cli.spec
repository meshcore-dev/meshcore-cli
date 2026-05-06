Name:           meshcore-cli
Version:        1.5.7
Release:        1%{?dist}
Summary:        CLI interface to MeshCore companion radios and repeaters
License:        MIT
URL:            https://github.com/fdlamotte/meshcore-cli
Source0:        %{url}/archive/v%{version}.tar.gz#/meshcore-cli-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel >= 3.10
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-hatchling
BuildRequires:  help2man

Requires:       python3 >= 3.10

%description
meshcore-cli is a tool that connects to your companion radio node (meshcore client)
over BLE, TCP or Serial and lets you interact with it from a terminal using a
command line interface.

Features:
- Interactive chat mode with mesh nodes
- Support for BLE, TCP, and Serial connections
- Message sending and receiving
- Repeater login and command execution
- Trace path visualization
- Script execution support

%prep
%autosetup -n meshcore-cli-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files meshcore_cli

# Generate and install man page
mkdir -p %{buildroot}%{_mandir}/man1
help2man -N %{buildroot}%{_bindir}/meshcli > %{buildroot}%{_mandir}/man1/meshcli.1 || true
help2man -N %{buildroot}%{_bindir}/meshcore-cli > %{buildroot}%{_mandir}/man1/meshcore-cli.1 || true

%files -f %{pyproject_files}
%doc README.md
%license LICENSE
%{_bindir}/meshcli
%{_bindir}/meshcore-cli
%{_mandir}/man1/meshcli.1*
%{_mandir}/man1/meshcore-cli.1*

%changelog
* Wed May 05 2026 Florent de Lamotte <florent@frizoncorrea.fr> - 1.5.7-1
- Initial release
