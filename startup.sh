#!/bin/bash

cd "${0%/*}"
source bin/activate
cd code/
python hawking.py
