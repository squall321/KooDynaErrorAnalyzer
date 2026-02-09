#!/bin/bash

cd "$(dirname "$0")"

if [ ! -f venv/bin/python ]; then
    echo "가상환경이 없습니다. install.sh를 먼저 실행하세요."
    exit 1
fi

export PYTHONPATH="$(pwd)/src"
venv/bin/python -m koodyna "$@"
