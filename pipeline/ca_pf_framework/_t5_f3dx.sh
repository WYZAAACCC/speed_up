#!/bin/bash
# _t5_f3dx.sh --- 查 `f3_pos_dx` 的定义来源（第 8 条的关键分支）
cd "$(dirname "$0")" || exit 1
echo '════ ① 它在哪里被写 ════'
grep -n 'f3_pos_dx' _bk_exp.py _bk_measure.py 2>/dev/null | head -10 | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ② 它的计算上下文（看是否读滞后/缓存量）════'
LN=$(grep -n 'f3_pos_dx' _bk_exp.py 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$LN" ]; then
  sed -n "$((LN-14)),$((LN+6))p" _bk_exp.py | cut -c1-128 | sed 's/^/  /'
else
  echo '  （_bk_exp.py 里没有；试 _bk_measure.py）'
  LN=$(grep -n 'f3_pos_dx' _bk_measure.py 2>/dev/null | head -1 | cut -d: -f1)
  [ -n "$LN" ] && sed -n "$((LN-14)),$((LN+6))p" _bk_measure.py | cut -c1-128 | sed 's/^/  /'
fi
echo
echo '════ ③ 检查点里有没有它（若不含 ⇒ 续跑后只能重算，重算路径与首次可能不同）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import numpy as np, glob, os
f = sorted(glob.glob('_exp/_bk_t5/dry_ck8A/ckpt/*.npz'))
if not f:
    print('  ⚠ 没有检查点')
else:
    with np.load(f[0], allow_pickle=False) as z:
        ks = sorted(z.files)
    print('  检查点键（%d 个）：' % len(ks))
    for i in range(0, len(ks), 6):
        print('     %s' % ks[i:i+6])
    hit = [k for k in ks if 'f3' in k.lower() or 'pos' in k.lower()]
    print('  ★ 含 f3/pos 的键：%s' % (hit or '**无**'))
PYEOF
