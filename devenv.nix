{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [ pkgs.git ];

  # https://devenv.sh/languages/
  # languages.rust.enable = true;
  languages.php = {
    enable = true;
    version = "8.4";
    extensions = ["imagick"];
    fpm.pools.web.settings = {
      "clear_env" = "no";
      "pm" = "dynamic";
      "pm.max_children" = 10;
      "pm.start_servers" = 2;
      "pm.min_spare_servers" = 1;
      "pm.max_spare_servers" = 10;
    };
    ini = ''
      memory_limit=128M
      max_execution_time=120
      post_max_size=16M
      upload_max_filesize=16M
    '';

  };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  services.mysql = {
    enable = true;
    ensureUsers = [{
      name = "ianseo";
      password = "ianseo";
      ensurePermissions = {
        "ianseo.*" = "ALL PRIVILEGES";
      };
    }];
    initialDatabases = [{name = "ianseo";}];
  };
  services.caddy = {
    enable = true;
    virtualHosts.":8000".extraConfig = ''
      root * Ianseo
      php_fastcgi unix/${config.languages.php.fpm.pools.web.socket}
      file_server
    '';
  };

  # https://devenv.sh/scripts/
  scripts.hello.exec = ''
    echo hello from $GREET
  '';

  enterShell = ''
    if [[ ! -d Ianseo ]]; then
      ${pkgs.wget}/bin/wget https://ianseo.net/Release/Ianseo_20250210.zip
      ${pkgs.unzip}/bin/unzip Ianseo_20250210.zip -d Ianseo
      rm Ianseo_20250210.zip
    fi
  '';

  # https://devenv.sh/tasks/
  # tasks = {
  #   "myproj:setup".exec = "mytool build";
  #   "devenv:enterShell".after = [ "myproj:setup" ];
  # };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
