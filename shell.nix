let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  envVars = ''
    export GIT_SSL_CAINFO="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
  '';

  pythonTest = pkgs.python39.withPackages (ps: with ps; [ pytest ]);

in pkgs.mkShell {
  name = "more-browser-session";
  buildInputs = with pkgs; [
    cacert
    entr
    zsh
  ] ++
  (with python39Packages; [
    build
    pylint
    pythonTest
    setuptools_scm
    twine
    wheel
  ]);
}
