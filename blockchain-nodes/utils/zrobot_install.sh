#!/bin/bash
set -e

# settings
export BRANCH="development"

mkdir -p /opt/code/github/zero-os
pushd /opt/code/github/zero-os

# cloning source code
git clone --depth=1 -b ${BRANCH} https://github.com/zero-os/0-robot.git
pushd 0-robot

pip3 install -e .
popd
