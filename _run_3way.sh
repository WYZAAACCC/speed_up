#!/bin/bash
cd /mnt/f/speed_up
/root/miniconda3/envs/ml/bin/python pipeline/ca_pf_framework/../../_patch_tie.py 2>/dev/null || /root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_patch_tie.py
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_patch_ti64_3way.py
/root/miniconda3/envs/ml/bin/python -c "import ast,io; ast.parse(io.open('/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py',encoding='utf-8').read()); print('syntax OK')"
OMP_NUM_THREADS=1 nohup /root/miniconda3/envs/ml/bin/python -u _ti64_cell.py > _ti64_cell4.log 2>&1 < /dev/null &
sleep 20; echo started