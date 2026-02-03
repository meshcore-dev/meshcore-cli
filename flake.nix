{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    inputs:
    inputs.flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = inputs.nixpkgs.legacyPackages.${system};

        lib = pkgs.lib;

        inherit (pkgs) python3Packages;

        meshcore = python3Packages.buildPythonPackage rec {
          pname = "meshcore";
          version = "2.2.7";
          pyproject = true;

          src = python3Packages.fetchPypi {
            inherit pname version;
            sha256 = "sha256-F7mjj6NuDvXgw0Zq3SbFiKCnXkAgm2EkxKToiL1VXJA=";
          };

          build-system = [ python3Packages.hatchling ];

          dependencies = [
            python3Packages.bleak
            python3Packages.pycayennelpp
            python3Packages.pyserial-asyncio-fast
          ];

          pythonImportsCheck = [ "meshcore" ];
        };

        pyproject = lib.importTOML ./pyproject.toml;
        version = pyproject.project.version;
      in
      {
        packages.meshcore-cli = python3Packages.buildPythonPackage {
          pname = "meshcore-cli";
          inherit version;

          src = ./.;

          pyproject = true;

          nativeBuildInputs = [
            python3Packages.hatchling
            python3Packages.setuptools
            python3Packages.wheel
          ];

          propagatedBuildInputs = [
            meshcore
            python3Packages.click
            python3Packages.prompt_toolkit
            python3Packages.pyserial
            python3Packages.requests
            python3Packages.pycryptodome
          ];

          doCheck = false;
        };
      }
    );
}
