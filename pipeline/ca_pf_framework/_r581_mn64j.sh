#!/bin/bash
# _r581_mn64j.sh --- ★★★★★ **臂 J：破"自限环"的判决实验**（R581-R128）
#
# ## 为什么需要它（R128 把因果链补全了）
# **R125 说"天花板 = `V × m`"，但 F（`B=74`、`m=12`）只给 13 根 —— 与"`B` 大 ⇒ 事件多 ⇒ `V` 大"矛盾。**
# **★ 补全后的模型（自限环）**：
# ```
# 总根数 ≤ V × m × ~0.4        （容量 × 利用率）
# V      ≤ 1 + n_fresh          （只有成功的 fresh 才加变体）
# n_fresh ≈ 成功事件数 / K
# 成功事件数 ≈ min(_tgt, 容量) × 达成率
# ⇒ **要更多根 ⇒ 要更大 V ⇒ 要更多成功的 fresh ⇒ 要更多容量 ⇒ 要更大 m**
# ⇒ **这是个**自限环**：光提 `B` 提不动它。**
# ```
# **★ 代入实测验证**：F（`B=74`、`_tgt=370`）若达成率 3.5% ⇒ 成功事件 ≈13 ⇒ `n_fresh`≈2 ⇒ `V`≈3
# ⇒ 容量 36 ⇒ 实得 13 = **36% 的容量** ✓ **自洽**
#
# ## 判决实验（本臂要回答的唯一问题）
# > **把 `m` 先提上去（容量 240），`V` 会不会跟着涨起来？**
# | 臂 | `m` | `B` | `_tgt` | 容量 `V×m`（若 `V` 涨到 12） | **预测** |
# |---|---|---|---|---|---|
# | E（已知） | **20** | 5 | 25 | 240 | `V`=1（**实测**） |
# | **J（本臂）** | **20** | **28** | **140** | **240** | **★ 若自限环成立 ⇒ `V` 应显著 >1；若 `V` 仍 =1 ⇒ 环另有约束** |
#
# **判据（预先写死）**：
# * **J 的 `V` ≥ 4** ⇒ 自限环**成立** ⇒ 处方 = **先提 `m` 再提 `B`**；
# * **J 的 `V` ≤ 2** ⇒ 自限环**不成立** ⇒ `V` 的约束在别处（如 `--nuc-fresh-every K` 或 `ed` 的选择）⇒ **回去查**。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64J_STEPS:-250}"
LOG=_w2_r581_mn64j.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R128：臂 J —— 破自限环的判决（m=20 + B=28）==="
say "阶段 1：等 N=64 上的 E/F/G/H/I 跑完（P33：N=64 可并发，但别与 N=160 抢内存）…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 720 ] && { say "❌ 等了 6 h ⇒ 退出"; exit 4; }
done
say "阶段 1 完成"

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 100 \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 28 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

for M in 20 37; do
  T="J${M}"
  laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($M)))")
  d="$ROOT/dry_$T"
  if [ -d "$d" ]; then say "跳过 $T（已存在）"; continue; fi
  avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
  if [ "$avail" -lt 1500 ]; then say "❌ 内存不足（${avail} MB）⇒ 停在 $T"; exit 3; fi
  say "起 $T：m=$M（nv=$((M * 12))）、B=28（cores 8-11）"
  taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag "$T" --laths "$laths" \
      --var-rule ed > "_w2_r581_mn64_${T}.log" 2>&1
  say "$T 结束 exit=$? Traceback=$(grep -c '^Traceback' "_w2_r581_mn64_${T}.log" || true)"
done

say "── ★ 判决表（V 是自限环的关键）──"
$PY - "$ROOT" <<'PYEOF'
import json, os, sys
from collections import Counter
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 100)
print('臂 J：破自限环的判决（m=20 / m=37，B=28）')
print('=' * 100)
print(' %-8s %-5s %-6s %-8s %-9s %-10s %s' % ('臂', 'm', 'B', 'V(实测)', '容量V*m', 'nslab', '判定'))
print(' ' + '-' * 92)
REF = {'E': (20, 5, 1, 10)}   # 已知参照：m=20/B=5 ⇒ V=1、nslab=10
for t, (m, b) in [('E', (20, 5)), ('J20', (20, 28)), ('J37', (37, 28))]:
    d = os.path.join(ROOT, 'dry_' + t)
    if not os.path.isdir(d):
        continue
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    if not snaps:
        continue
    z = np.load(os.path.join(d, snaps[-1]))
    if 'region' not in z or 'vmap_keys' not in z:
        continue
    reg = z['region']
    vm = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                  [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
    byvar = Counter()
    for f in np.unique(reg):
        f = int(f)
        if f > 0:
            byvar[vm.get(f, -1)] += 1
    V = len(byvar)
    verdict = ''
    if t != 'E':
        verdict = '✅ 环成立（V≥4）' if V >= 4 else '❌ 环不成立（V≤3）⇒ 回去查'
    print(' %-8s %-5d %-6d %-8d %-9d %-10s %s'
          % (t, m, b, V, V * m, sum(byvar.values()), verdict))
print()
print('  ★ 参照：E（m=20/B=5）实测 V=1、nslab=10')
print('  ★ 判据：J20/J37 的 V ≥ 4 ⇒ 自限环成立（先提 m 再提 B）；V ≤ 2 ⇒ 环另有约束')
print('=' * 100)
PYEOF
say "=== R581 MN64J DONE ==="
