# https://devenv.sh
{ pkgs, ... }:

{
  packages = with pkgs; [ 
    black
    git
    pylint
  ];

  languages.python = {
    enable = true;
    poetry = {
      enable = true;
      package = pkgs.poetry;
    };
  };
}
