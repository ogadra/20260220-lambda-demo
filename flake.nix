{
  description = "AWS Lambda demo development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfreePredicate = pkg:
            builtins.elem (pkgs.lib.getName pkg) [ "terraform" ];
        };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            awscli2
            terraform
            zip
          ];

          shellHook = ''
            echo "lambda-demo dev shell"
            echo "  aws     : $(aws --version 2>&1 | head -1)"
            echo "  terraform: $(terraform version -json 2>/dev/null | ${pkgs.jq}/bin/jq -r '.terraform_version' 2>/dev/null || terraform version | head -1)"
          '';
        };
      });
}
