#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
exec /root/miniconda3/envs/ml/bin/python -u _t19H_conv.py --advs central,proj2,upwind --dxs 25,18.75,12.5
