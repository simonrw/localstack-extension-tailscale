{ pkgs ? import <nixpkgs> { } }:
with pkgs;
mkShell {
  packages = [
    python3
    python3Packages.venvShellHook
    go
    docker
  ];

  venvDir = ".venv";

  postVenvCreation = ''
    python -m pip install pip-tools
  '';

  postShellHook = ''
    export VENV_DIR=$VIRTUAL_ENV
  '';
}

