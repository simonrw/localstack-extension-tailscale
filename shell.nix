{ pkgs ? import <nixpkgs> { } }:
with pkgs;
mkShell {
  packages = [
    python3
    python3Packages.venvShellHook
    go
    docker
    uv
    ruff
  ];

  venvDir = ".venv";

  postVenvCreation = ''
  '';

  postShellHook = ''
    export VENV_DIR=$VIRTUAL_ENV
  '';
}

