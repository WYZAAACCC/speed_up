#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh; conda activate moose
cd /root/bench/run && timeout 900 /root/miniconda3/envs/ml/bin/python -u /mnt/f/speed_up/_exaca_geom_test.py 2>&1 | tail -22