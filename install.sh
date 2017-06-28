#!/bin/bash

sudo apt-get install -y graphviz
python3 -m venv .venv
.venv/bin/python3 -m pip install wheel
.venv/bin/python3 -m pip install -r requirements.txt
