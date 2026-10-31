#!/usr/bin/env bash
set -euo pipefail
printf 'Disk before cleanup\n'; df -h /
# No Android SDK is needed for prebuilt image inspection; emulator job is separate.
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /usr/local/.ghcup /opt/hostedtoolcache/CodeQL /usr/local/share/boost
sudo docker image prune -af >/dev/null 2>&1 || true
sudo apt-get clean
printf 'Disk after cleanup\n'; df -h /
