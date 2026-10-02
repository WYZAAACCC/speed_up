#!/bin/bash
# _r581_mn64k.sh --- ★★★★★★ **臂 K：C5/C6 的**判决实验**（R581-R136）
#
# ## 根因（R136 查明）
# `fresh` 请求**发生了**但**被拒**（代码注释逐字：「**待机位点用尽 / 落位失败**」）
# ⇒ 当场退回 `stack` ⇒ 没有新变体 ⇒ `V` ≤ 2 ⇒ C5/C6 都不可能。
# **直接证据**：日志里「`fresh` 被拒 ⇒ 退回 `stack`」的次数随 `B` 涨：A=0/B=1/C=1/D=1/E=1/**F=3**/**G=6**。
#
# ## 判决实验（唯一要回答的问题）
# > **把 `--nuc-init`（待机位点数）调大，`V` 会不会上去？**
# | 臂 | `--nuc-init` | `--var-rule` | 预测 |
# |---|---|---|---|
# | E（已知） | **6** | `ed` | `V`=1（实测） |
# | **K1** | **64** | `ed` | **★ 若根因对 ⇒ `V` 应 > 2** |
# | **K2** | **64** | **`doublet`** | **★ 若"挑新变体"那条也对 ⇒ `V` 应更高** |
#
# **判据（预先写死）**：
# * **K1 的 `V` ≥ 4** ⇒ **根因坐实** ⇒ **C5/C6 不需要改口径，只需调 `--nuc-init`**；
# * **K1 的 `V` ≤ 2** ⇒ **根因**不成立** ⇒ `fresh` 被拒与位点数无关 ⇒ **回去查 `nucleate()` 的拒绝分支**；
# * **K2 的 `V` > K1 的 `V`** ⇒ **"挑新变体"那条也成立** ⇒ `--var-rule doublet` 该用。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64K_STEPS:-250}"
LOG=_w2_r581_mn64k.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R136：臂 K —— C5/C6 判决（--nuc-init 调大）==="
say "阶段 1：等 N=64 上的其它臂跑完…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 720 ] && { say "❌ 等了 6 h ⇒ 退出"; exit 4; }
done
say "阶段 1 完成"

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 100 \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-block-target 5 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

M=20
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($M)))")

for spec in "K1 64 ed" "K2 64 doublet" "K3 6 ed"; do
  set -- $spec
  T=$1; NI=$2; VR=$3
  d="$ROOT/dry_$T"
  if [ -d "$d" ]; then say "跳过 $T（已存在）"; continue; fi
  avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
  if [ "$avail" -lt 1500 ]; then say "❌ 内存不足（${avail} MB）⇒ 停在 $T"; exit 3; fi
  say "起 $T：--nuc-init $NI、--var-rule $VR（cores 8-11）"
  taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag "$T" --laths "$laths" \
      --nuc-init "$NI" --var-rule "$VR" > "_w2_r581_mn64_${T}.log" 2>&1
  nr=$(grep -c 'fresh` 被拒' "_w2_r581_mn64_${T}.log" 2>/dev/null || echo '?')
  say "$T 结束 exit=$?；「fresh 被拒」$nr 次；Traceback=$(grep -c '^Traceback' "_w2_r581_mn64_${T}.log" || true)"
done

say "── ★ 判决表（`V` 是根因的关键）──"
$PY - "$ROOT" <<'PYEOF'
import json, os, sys
from collections import Counter
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 100)
print('臂 K：`--nuc-init` 调大 ⇒ `V` 会不会上去？')
print('=' * 100)
print(' %-6s %-10s %-10s %-8s %-9s %-10s %s'
      % ('臂', 'nuc-init', 'var-rule', 'V', 'nslab', 'fresh 拒绝', '判定'))
print(' ' + '-' * 88)
for t, ni, vr in [('E', 6, 'ed'), ('K3', 6, 'ed'), ('K1', 64, 'ed'), ('K2', 64, 'doublet')]:
    d = os.path.join(ROOT, 'dry_' + t)
    if not os.path.isdir(d):
        continue
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    V = ns = '?'
    if snaps:
        z = np.load(os.path.join(d, snaps[-1]))
        if 'region' in z and 'vmap_keys' in z:
            reg = z['region']
            vm = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                          [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
            by = Counter()
            for f in np.unique(reg):
                f = int(f)
                if f > 0:
                    by[vm.get(f, -1)] += 1
            V = len(by); ns = sum(by.values())
    lg = '_w2_r581_mn64_%s.log' % t
    nrej = '?'
    if os.path.exists(lg):
        nrej = sum(1 for _ in open(lg, encoding='utf-8', errors='replace')
                   if 'fresh` 被拒' in _)
    verdict = ''
    if t in ('K1', 'K3') and isinstance(V, int):
        verdict = '✅ 根因坐实（V≥4）' if V >= 4 else '❌ 根因不成立（V≤2）⇒ 回去查 nucleate()'
    if t == 'K2' and isinstance(V, int):
        verdict = '（与 K1 比：更大 ⇒ "挑新变体"也成立）'
    print(' %-6s %-10d %-10s %-8s %-9s %-10s %s'
          % (t, ni, vr, V, ns, nrej, verdict))
print()
print('  ★ 判据：K1 的 V ≥ 4 ⇒ 根因坐实、C5/C6 不必改口径；V ≤ 2 ⇒ 根因不成立')
print('=' * 100)
PYEOF
say "=== R581 MN64K DONE ==="
