#!/bin/bash
# _t5_c2new.sh --- 判据② 在**最新快照**上（含新增的那根板条）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
D=_exp/_bk_t5/dry_t5H3
S=$(ls -1 $D/snap_*.npz 2>/dev/null | sort | tail -1)
echo "★ 最新快照 = $S"
echo
echo '════ ① band 是否可用（判据② 需要它）════'
$PY - "$S" <<'PYEOF'
import numpy as np, sys
with np.load(sys.argv[1], allow_pickle=False) as z:
    ks = set(z.files)
    for k in ('band_idx', 'band_val', 'band_fld', 'region', 'phi'):
        print('    含 %-10s = %s' % (k, k in ks))
    if 'band_fld' in ks:
        f = np.asarray(z['band_fld']).ravel()
        print('    band_fld 覆盖的场 =', sorted(set(int(x) for x in f.tolist()))[:30])
    if 'nslab_n' in ks:
        print('    nslab_n =', np.asarray(z['nslab_n']).ravel()[:1])
PYEOF
echo
echo '════ ② 判据②（投影法 + t_wf 互证）════'
if [ -n "$S" ]; then
  taskset -c 16-19 $PY _t5_proj.py "$S" 2>&1 | tail -24
else
  echo '  ⚠ 没有快照'
fi
