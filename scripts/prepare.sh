#!/usr/bin/env bash
# Download the pinned sources and JDK used by the Docker build.
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"

download() {
    local url=$1 filename=$2 checksum=$3
    if [[ ! -f "$filename" ]]; then
        curl -L --fail --retry 2 "$url" -o "$filename"
    fi
    printf '%s  %s\n' "$checksum" "$filename" | sha256sum --check -
}

mkdir -p .local/downloads
download 'https://codeload.github.com/OrderLab/Legolas/tar.gz/84278d313f98' \
    .local/downloads/legolas.tar.gz 03aebfba5a2335c180c73d8fd30c0165c628a5423ac9104530807a9b07e5d91d
download 'https://codeload.github.com/apache/zookeeper/tar.gz/refs/tags/release-3.6.2' \
    .local/downloads/zookeeper.tar.gz 42fed2bc5c266bc9640d4581265de8b1d66a0837576505e189c7e7b613f78e6b
download 'https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz' \
    .local/downloads/jdk8.tar.gz 9c70e102f527ac674ac2fe9c7d47b9a04e2d19842ba5ab8e9b33f368bbadfaea
for component in legolas zookeeper jdk8; do
    if [[ ! -d ".local/$component" ]]; then
        mkdir ".local/$component"
        tar -xzf ".local/downloads/$component.tar.gz" --strip-components=1 -C ".local/$component"
    fi
done
