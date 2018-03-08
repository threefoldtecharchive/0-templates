#!/bin/bash
set -e

# settings
export BRANCH="master"

mkdir -p /opt/code/github/jumpscale
pushd /opt/code/github/jumpscale

# cloning source code
git clone --depth=1 -b ${BRANCH} https://github.com/Jumpscale/0-robot
pushd 0-robot
pip3 install -r requirements.txt
pip3 install .
popd