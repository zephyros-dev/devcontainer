import argparse
import os
import platform
import re
import subprocess
from pathlib import Path

import yaml

GO_ARCH_DICT = {
    "x86_64": "amd64",
    "aarch64": "arm64",
}
MISE_ARCH_DICT = {"x86_64": "x64", "aarch64": "arm64"}

go_arch = GO_ARCH_DICT[platform.machine()]
mise_arch = MISE_ARCH_DICT[platform.machine()]


def insert_multiline_if_missing(file_path, multiline_str):
    """
    Inserts a multiline string into a file if the exact sequence of lines does not already exist.

    Args:
        file_path (str): The path to the file to be modified.
        multiline_str (str): The multiline string to be inserted.
    """
    # Normalize line endings
    multiline_str.strip().splitlines()

    if not Path(file_path).exists():
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).touch()

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # If the exact sequence already exists, do nothing
    if multiline_str.strip() in content:
        print(f"Multiline string already exists in the file {file_path}")
        return

    # Append the multiline string to the end of the file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("\n" + multiline_str.strip() + "\n")

    print(f"Multiline string inserted into the file {file_path}")


def check_version(command, desired_version):
    # Install the tools if tools is not installed or current version is different
    current_version = subprocess.run(
        command, shell=True, capture_output=True, text=True
    )
    if "not found" in current_version.stderr or re.search(
        r"\d+\.\d+\.\d+",
        current_version.stdout,
    ).group(0) != desired_version.strip("v"):
        return True
    else:
        return False


def install_podman():
    if Path("dependencies.yaml").exists():
        dependencies_version = yaml.safe_load(Path("dependencies.yaml").read_text())
    else:
        dependencies_version = {}

    if "containers/podman" in dependencies_version:
        # Install latest version of podman
        podman_path = Path.home() / "bin/podman"

        PODMAN_VERSION = dependencies_version["containers/podman"]
        if check_version("docker --version", PODMAN_VERSION):
            subprocess.run(
                f"curl -Lo {Path.home() / 'podman.tar.gz'} https://github.com/containers/podman/releases/download/{PODMAN_VERSION}/podman-remote-static-linux_{go_arch}.tar.gz",
                shell=True,
            )
            subprocess.run(
                f"tar -zxvf {Path.home() / 'podman.tar.gz'} -C {Path.home()}",
                shell=True,
            )
            subprocess.run(
                f"mv {Path.home()}/bin/podman-remote-static-linux_{go_arch} {podman_path}",
                shell=True,
            )

            (Path.home() / ".local/bin").mkdir(parents=True, exist_ok=True)
            subprocess.run(
                f"ln --symbolic --force {podman_path} {Path.home()}/.local/bin/docker",
                shell=True,
            )


def install_mise():
    if (Path(os.getcwd()) / "mise.toml").exists():
        MISE_VERSION = yaml.safe_load(
            Path(".devcontainer/dependencies.yaml").read_text()
        )["jdx/mise"]
        mise_bin_path = Path.home() / ".local/bin/mise"
        mise_bin_path.parent.mkdir(parents=True, exist_ok=True)
        local_bin_path = Path.home() / ".local/bin/"
        local_bin_path.mkdir(parents=True, exist_ok=True)
        if check_version("mise --version", MISE_VERSION):
            subprocess.run(
                f"curl -Lo {mise_bin_path} https://github.com/jdx/mise/releases/download/{MISE_VERSION}/mise-{MISE_VERSION}-linux-{mise_arch}",
                shell=True,
            )
            os.chmod(mise_bin_path, 0o700)
        (Path(Path.home()) / ".config/mise").mkdir(parents=True, exist_ok=True)

        if not (Path.home() / ".config/mise/config.toml").is_symlink():
            Path(Path.home() / ".config/mise/config.toml").symlink_to(
                Path(os.getcwd()) / ".devcontainer/config.toml"
            )
        subprocess.run(["mise", "trust", "--all"])
        for k, v in {
            "bash": Path.home() / ".bashrc",
            "fish": Path.home() / ".config/fish/config.fish",
        }.items():
            activate_string = subprocess.run(
                f"mise activate {k}", shell=True, capture_output=True, text=True
            )
            insert_multiline_if_missing(v, activate_string.stdout)
    subprocess.run(["mise", "install", "--yes"])


def install_aqua():
    # Check if aqua.yaml is present
    if (Path(os.getcwd()) / "aqua.yaml").exists():
        AQUA_VERSION = yaml.safe_load(
            Path(".devcontainer/dependencies.yaml").read_text()
        )["aquaproj/aqua"]
        aqua_bin_dir_path = Path.home() / ".local/share/aquaproj-aqua/bin"
        aqua_bin_dir_path.mkdir(parents=True, exist_ok=True)
        local_bin_path = Path.home() / ".local/bin/"
        local_bin_path.mkdir(parents=True, exist_ok=True)
        if check_version("aqua --version", AQUA_VERSION):
            subprocess.run(
                f"curl -Lo {Path.home() / 'aqua.tar.gz'} https://github.com/aquaproj/aqua/releases/download/{AQUA_VERSION}/aqua_linux_{go_arch}.tar.gz",
                shell=True,
            )
            subprocess.run(
                f"tar -zxvf {Path.home() / 'aqua.tar.gz'} -C {local_bin_path} aqua",
                shell=True,
            )

        (Path(Path.home()) / ".config/aquaproj-aqua").mkdir(parents=True, exist_ok=True)

        if not (Path.home() / ".config/aquaproj-aqua/aqua.yaml").is_symlink():
            Path(Path.home() / ".config/aquaproj-aqua/aqua.yaml").symlink_to(
                Path(os.getcwd()) / "aqua.yaml"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup devcontainer")
    parser.add_argument(
        "--stage",
        help="stage to run",
        default="all",
    )

    args = parser.parse_args()

    os.chdir("../")

    if args.stage == "all" or args.stage == "onCreateCommand":
        install_podman()
        install_aqua()
        install_mise()
        subprocess.run("aqua install --all", shell=True)

    if args.stage == "all" or args.stage == "postAttachCommand":
        if Path(".pre-commit-config.yaml").exists():
            subprocess.run(
                "git config --global init.templateDir ~/.git-template", shell=True
            )
            subprocess.run(
                "pre-commit init-templatedir -t pre-commit ~/.git-template",
                shell=True,
            )
            subprocess.run("pre-commit install", shell=True)
        if Path("install.py").exists() and Path("uv.lock").exists():
            subprocess.run(["uv", "sync"])
            subprocess.run(["uv", "run", "install.py"])
