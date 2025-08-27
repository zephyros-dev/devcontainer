import argparse
import os
import platform
import re
import subprocess
import tomllib
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

    if multiline_str in Path(file_path).read_text():
        print(f"Multiline string already exists in the file {file_path}")
        return
    else:
        with open(file_path, "a") as f:
            f.write("\n" + multiline_str + "\n")
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
    if Path("mise.toml").exists():
        if "podman" in tomllib.loads(Path("mise.toml").read_text())["tools"]:
            podman_path = subprocess.run(
                "mise which podman", shell=True, capture_output=True, text=True
            ).stdout.strip()
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
        install_mise()
        subprocess.run(["mise", "install"])
        install_podman()

    if args.stage == "all" or args.stage == "postAttachCommand":
        os.environ["PATH"] = (
            f"{Path.home()}/.local/share/mise/shims:{os.environ['PATH']}"
        )
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
