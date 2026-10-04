#!/bin/bash
# _t5_eps0prod.sh --- ★★★★★★ 读 `_bk_exp.py` 传给 `LevelSetMulti` 的**真实 `eps0` 实参**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `eps0` 在 `_bk_exp.py` 里的构造/赋值处 ════'
grep -nE 'eps0' _bk_exp.py | grep -viE '^\s*[0-9]+:\s*#' | head -22 | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ② 数值定义段（含数字的 eps0 行）════'
grep -nE 'eps0 *= *(np\.|\[)|EPS0|eps0 *= *\[|_EPS0|e0 *=' _bk_exp.py | head -12 | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ③ 若在别的模块（如 windowB_km / windowB_acct）════'
grep -rnE 'eps0 *= *(\[|np\.(array|asarray)\()' windowB_km.py windowB_acct.py windowB_pf3d.py 2>/dev/null \
  | head -10 | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ④ ★ 直接从**运行的进程内存**里读不到，改从**断点文件**里找 phi/vmap 之外的信息 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import glob, os
import numpy as np
for P in sorted(glob.glob('_exp/_bk_t5/dry_t5B4D/ckpt/*.npz'))[:1]:
    with np.load(P, allow_pickle=False) as z:
        print('  断点键 = %s' % list(z.files))
        for k in z.files:
            a = np.asarray(z[k])
            if a.dtype.kind == 'f' and a.ndim <= 2 and a.size <= 400:
                print('     %-14s shape=%s  样例=%s' % (k, a.shape, np.round(a.ravel()[:6], 6)))
PYEOF
echo
echo '════ ⑤ 最快的路：让 Python 直接问引擎的类默认值 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import re
src = open('_bk_exp.py', encoding='utf-8').read()
# 找 LevelSetMulti(...) 调用里的 eps0=
for m in re.finditer(r'eps0\s*=\s*([^,\n]+)', src):
    ln = src[:m.start()].count('\n') + 1
    print('  第 %-6d 行：eps0 = %s' % (ln, m.group(1).strip()[:90]))
PYEOF
