#!/bin/bash
set -e

# settings
export BRANCH=${1:-"development"}

mkdir -p /opt/code/github/threefoldtech
sudo chown -R $USER:$USER /opt/code/github/threefoldtech
pushd /opt/code/github/threefoldtech

# cloning source code
git clone --depth=1 -b ${BRANCH} https://github.com/threefoldtech/0-robot
pushd 0-robot
pip3 install -e .
popd