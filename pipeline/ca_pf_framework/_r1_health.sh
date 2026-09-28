#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "--- conda env ---"
ls -d /root/miniconda3/envs/ml && /root/miniconda3/envs/ml/bin/python -c 'import numpy, scipy; print("py OK", numpy.__version__, scipy.__version__)'
echo "--- repo ---"
ls windowB_surface.py windowB_par.py _r1_exp.py _r1_analyze.py >/dev/null && echo "repo OK"
echo "--- 残留进程 ---"
ps -eo pid,args | grep -E '_r1_exp|_r1_drive|_r1_selfac' | grep -v grep || echo "无"
echo "--- _exp 目录 ---"
ls _exp/ | tr '\n' ' '; echo
echo "--- mem ---"; free -g | head -2
