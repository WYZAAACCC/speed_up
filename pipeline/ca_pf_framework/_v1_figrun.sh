#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _v1_patch2.py
seq 0 3 | xargs -P 4 -I{} env OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python _v1_worker.py t3_aniso_law:{}
/root/miniconda3/envs/ml/bin/python _v1_fig.py