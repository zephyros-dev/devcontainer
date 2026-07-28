FROM ghcr.io/astral-sh/uv:0.12.0-debian-slim@sha256:b3781c0d61af34f63032d5221a6bf2e46b2a16225a531d2dea0836f09861c190

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update \
    && apt install -y --no-install-recommends \
    ca-certificates \
    curl \
    fish \
    git \
    # Ansbile
    openssh-client \
    openssl \
    sshpass \
    # Openwrt
    rsync \
    # Fix locales for python
    # https://stackoverflow.com/a/28406007
    locales \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

ARG USERNAME
ARG workspaceFolder
RUN useradd --create-home --shell /bin/bash ${USERNAME}

USER ${USERNAME}
RUN mkdir -p \
    ~/.ansible \
    ~/.cache \
    ~/.config/sops/age \
    ~/.local/bin \
    ~/.local/share/aquaproj-aqua \
    ~/.local/share/fish \
    ~/.local/share/uv \
    ~/.ssh \
    ~/.terraform.d/plugin-cache \
    ~/bin

ENV PATH=/home/${USERNAME}/.local/share/aquaproj-aqua/bin:${workspaceFolder}/.venv/bin:${workspaceFolder}/.devcontainer/.venv/bin:$PATH
