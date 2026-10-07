#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== env check ==="
$PY -c "
import numpy, scipy, sys
print('python', sys.version.split()[0])
print('numpy', numpy.__version__, ' scipy', scipy.__version__)
for m in ('numba','numexpr','torch','cython'):
    try:
        __import__(m); print(m, 'OK')
    except Exception as e:
        print(m, 'MISSING', type(e).__name__)
import numpy as np
print('numpy threads-related config:')
try:
    print('  np.show_config() -> 见下')
except Exception as e:
    print(e)
"
echo "=== run probe N=192 ==="
$PY -u _r1_par.py --N 192 --reps 3 --maxth 20 > _w2_r1par_N192.log 2>&1
echo "rc=$?"
tail -120 _w2_r1par_N192.log
