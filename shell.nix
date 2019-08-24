{ usePipenvShell ? false }:
let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  envVars = ''
    export GIT_SSL_CAINFO="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"; 
  '';

in pkgs.stdenv.mkDerivation {
  src = null;
  name = "more-browser-session-dev-env";
  phases = [];
  propagatedBuildInputs = with pkgs; [ 
    cacert
    entr
    pipenv
    zsh
  ] ++
  (with python37Packages; [
    autopep8
    ipdb
    mypy
    pylint
    python 
    setuptools_scm
    twine
    wheel
  ]);
  shellHook = envVars + (lib.optionalString 
                         usePipenvShell "SHELL=`which zsh` exec pipenv shell --fancy");
}
