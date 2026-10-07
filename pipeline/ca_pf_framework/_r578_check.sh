#!/bin/bash
# _r578_check.sh --- R578：语法 + 新开关的**逐位判据 + 负对照**（快检，不跑长算例）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== R578 CHECK $(date '+%F %T') ==="
$PY - <<'PYEOF'
import os, sys
sys.path.insert(0, os.getcwd())
import py_compile
bad = 0
for f in ('windowB_acct.py', 'windowB_par.py', 'windowB_pf3d.py',
          'windowB_surface.py', '_bk_exp.py'):
    try:
        py_compile.compile(f, doraise=True)
        print('  C1 %-20s py_compile OK' % f)
    except Exception as e:
        print('  C1 %-20s FAIL %r' % (f, e)); bad = 1
import numpy as np
import windowB_surface as W
import windowB_par as PAR
# C2 构造参数校验（错值必须硬失败）
for kw, val in (('k_loop_mode', 'x'), ('act_mode', 'x'), ('argmin2_mode', 'x')):
    try:
        W.LevelSetMulti(8, 8 * 0.0625, **{kw: val})
        print('  C2 %s=%r **没报错** ❌' % (kw, val)); bad = 1
    except ValueError:
        print('  C2 %s=%r 正确硬失败 ✅' % (kw, val))
    except Exception as e:
        print('  C2 %s=%r 报了别的错 %r ⚠' % (kw, val, e))
# C3 argmin2 两模式逐位
rng = np.random.default_rng(5)
F = rng.random((9, 24, 24, 24))
k0, l0 = PAR.ParCtx.argmin2(PAR.ParCtx(1), F, mode='legacy')
k1, l1 = PAR.ParCtx.argmin2(PAR.ParCtx(1), F, mode='copyto')
d = max(int(np.max(np.abs(k0 - k1))), int(np.max(np.abs(l0 - l1))))
print('  C3 argmin2 legacy vs copyto: max|Δ| = %d ⇒ %s'
      % (d, 'OK' if d == 0 else 'FAIL'))
bad = bad or (d != 0)
# C3b 负对照：★ 两次写错，都记账（`AGENTS.md` 教训 15：被比较的量本身是否随扰动变化？）
#   v1 `F2[0,0,0,0] -= 0.5`  —— 把场 0 变小 ⇒ 场 0 **仍是** argmin ⇒ k 不变
#   v2 `F2[0,0,0,0] += 10`   —— 但那个胞的 argmin **本来就不是场 0**（随机数据 1/9 概率）
#                              ⇒ 抬高它也不改变谁赢
#   ⇒ 正确做法：**先找一胞、确认它现在的 winner 就是场 0**，再抬高场 0。
idx = np.argwhere(k0 == 0)
a, b, c = (int(v) for v in idx[0])
F2 = F.copy()
F2[0, a, b, c] += 10.0
k2, l2 = PAR.ParCtx.argmin2(PAR.ParCtx(1), F2, mode='legacy')
d2 = max(int(np.max(np.abs(k0 - k2))), int(np.max(np.abs(l0 - l2))))
print('  C3b 负对照（胞 %d,%d,%d 的 winner 本是场0，抬高场0 10）: max|Δ| = %d ⇒ %s'
      % (a, b, c, d2, 'OK 有分辨力' if d2 > 0 else 'FAIL 没分辨力'))
bad = bad or (d2 == 0)
# C4 act 两模式同一集合
karr = rng.integers(0, 25, size=(32, 32, 32)).astype(np.intp)
larr = rng.integers(0, 25, size=(32, 32, 32)).astype(np.intp)
a0 = np.unique(np.concatenate((np.unique(karr), np.unique(larr))))
c = np.bincount(karr.ravel(), minlength=25); c += np.bincount(larr.ravel(), minlength=25)
a1 = np.flatnonzero(c)
print('  C4 act unique=%s bincount=%s ⇒ %s'
      % (a0.tolist(), a1.tolist(),
         'OK' if np.array_equal(a0, a1) else 'FAIL'))
bad = bad or (not np.array_equal(a0, a1))
print('  === RESULT: %s ===' % ('ALL PASS' if bad == 0 else 'FAIL'))
sys.exit(bad)
PYEOF
echo "=== R578 CHECK DONE rc=$? ==="
