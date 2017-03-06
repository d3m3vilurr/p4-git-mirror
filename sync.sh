#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
docker run --rm -i -v $HOME/.ssh:/root/.ssh -v $DIR/config.py:/opt/config.py -v $DIR/mirrors:/opt/mirrors sulee/p4-git-mirror $@
