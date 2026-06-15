#!/usr/bin/env bash
# ABOUTME: One-time bootstrap installing Docker Engine + Compose plugin on the Debian 13 demo VPS.
# ABOUTME: Idempotent; run with sudo. Adds the invoking user to the docker group.
set -euo pipefail

# Official apt-repository method, verified against docs.docker.com/engine/install/debian
# (Debian 13 "trixie" is officially supported as of 2026-06).

TARGET_USER="${SUDO_USER:-$(id -un)}"

echo "==> [1/6] Checking for an existing Docker installation..."
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "    Already installed: $(docker --version)"
else
  echo "==> [2/6] Removing any conflicting distro packages (safe if none present)..."
  conflicts="$(dpkg --get-selections docker.io docker-compose docker-doc podman-docker containerd runc 2>/dev/null | cut -f1 || true)"
  if [ -n "${conflicts}" ]; then
    apt-get remove -y ${conflicts} || true
  fi

  echo "==> [3/6] Configuring Docker's apt repository and GPG key..."
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "${VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

  echo "==> [4/6] Installing Docker Engine and the Compose plugin..."
  apt-get update -qq
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "==> [5/6] Enabling and starting the Docker service..."
systemctl enable --now docker

echo "==> [6/6] Adding user '${TARGET_USER}' to the docker group..."
usermod -aG docker "${TARGET_USER}"

echo
echo "Done. Installed versions:"
docker --version
docker compose version
echo
echo "NOTE: '${TARGET_USER}' must open a NEW shell/SSH session for docker-group"
echo "      membership to take effect. Confirm with 'docker ps' (no sudo)."
