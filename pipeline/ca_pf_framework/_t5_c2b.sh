#!/bin/bash
# _t5_c2b.sh --- 找**带 band 的最新快照**并跑判据②
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
D=_exp/_bk_t5/dry_t5H3
echo '════ 哪些快照带 band（逐个数 band_fld）════'
for S in $(ls -1 $D/snap_*.npz 2>/dev/null | sort); do
  HAS=$($PY -c "
import numpy as np,sys
with np.load('$S',allow_pickle=False) as z:
    print('Y' if 'band_fld' in z.files else 'N')
" 2>/dev/null)
  [ "$HAS" = "Y" ] && echo "  ✅ $S"
done
echo
S=$($PY - <<'PYEOF'
import glob, numpy as np, os
best = None
for s in sorted(glob.glob('_exp/_bk_t5/dry_t5H3/snap_*.npz')):
    try:
        with np.load(s, allow_pickle=False) as z:
            if 'band_fld' in z.files:
                best = s
    except Exception:
        pass
print(best or '')
PYEOF
)
echo "★ 带 band 的最新快照 = ${S:-（无）}"
[ -z "$S" ] && { echo '  ⇒ 本臂的 band 每 200 步；若最近的 200 倍数还没写到，就等下一个'; exit 0; }
echo
taskset -c 16-19 $PY _t5_proj.py "$S" 2>&1 | tail -26
