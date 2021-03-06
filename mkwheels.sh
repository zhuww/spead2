#!/bin/sh
set -e

sudo docker build --pull -t ska-sa/spead2/manylinux1 -f manylinux1/Dockerfile .
mkdir -p wheelhouse
sudo docker run --rm -v "$PWD/wheelhouse:/wheelhouse" ska-sa/spead2/manylinux1 sh -c 'cp -v /output/*.whl /wheelhouse'
sudo chown `id -u`:`id -g` wheelhouse/*.whl
