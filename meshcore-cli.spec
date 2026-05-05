Name:           meshcore-cli
Version:        1.5.7
Release:        1%{?dist}
Summary:        CLI interface to MeshCore companion radios and repeaters
License:        MIT
URL:            https://github.com/fdlamotte/meshcore-cli
Source0:        %{url}/archive/v%{version}.tar.gz#/meshcore-cli-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel >= 3.10
BuildRequires:  python3-hatchling
BuildRequires:  python3-pip
BuildRequires:  help2man

Requires:       python3 >= 3.10
Requires:       python3-meshcore >= 2.3.7
Requires:       python3-bleak >= 0.22
Requires:       python3-prompt-toolkit >= 3.0.50
Requires:       python3-requests >= 2.28.0

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
%py3_build

%install
%py3_install

# Generate and install man page
help2man -N %{buildroot}%{_bindir}/meshcli > %{buildroot}%{_mandir}/man1/meshcli.1 || true
help2man -N %{buildroot}%{_bindir}/meshcore-cli > %{buildroot}%{_mandir}/man1/meshcore-cli.1 || true

%files
%doc README.md
%license LICENSE
%{_bindir}/meshcli
%{_bindir}/meshcore-cli
%{python3_sitelib}/meshcore_cli/
%{python3_sitelib}/meshcore_cli-%{version}.dist-info/
%{_mandir}/man1/meshcli.1*
%{_mandir}/man1/meshcore-cli.1*

%changelog
* Wed May 05 2026 Florent de Lamotte <florent@frizoncorrea.fr> - 1.5.7-1
- Initial release
