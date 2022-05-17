let
  sources = import nix/sources.nix {};
  pkgs = import sources.nixpkgs {};
  lib = pkgs.lib;
  envVars = ''
    export GIT_SSL_CAINFO="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
  '';

in pkgs.mkShell {
  name = "more-browser-session";
  buildInputs = with pkgs; [
    entr
    niv
  ] ++
  (with pkgs.python310Packages; [
    black
    build
    isort
    interpreter
    pylint
    setuptools_scm
    twine
    wheel
  ]);
}
