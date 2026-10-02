#!/bin/bash
# _r581_mn64h.sh --- ★★★★★ **臂 I 组：`ed` vs `random` 的**干净**多 seed 对照（消 R114 的混淆）**
#
# ## 为什么需要（R114 查出的混淆）
# 臂 B（`ed`）与臂 D（`random`）**只差 `--var-rule`** —— 但 **`random` 会消耗 `rng`**（`ed` 不消耗）
# ⇒ **两臂的形核位点序列也不同** ⇒ **不是单变量对照** ⇒ R108/R113 的 `V`=2 vs 1 **不干净**。
#
# ## 干净做法：**扫 `--eng-seed`**（形核位点的种子，`_bk_exp.py:3101`）
# | 组 | `--var-rule` | `--eng-seed` |
# |---|---|---|
# | **ed** | `ed` | **11 / 23 / 37** |
# | **rn** | `random` | **11 / 23 / 37** |
# **⇒ 每臂的 `rng` 流不同 ⇒ 位点序列不同 ⇒ 把"位点差异"变成**噪声**（而不是混淆）。**
#
# ## 判据（**预先写死**）
# * **`ed` 的 `V` 分布显著高于 `random`** ⇒ R113 成立（有统计支撑）；
# * **两者重叠** ⇒ R108/R113 的差别是噪声 ⇒ **`--var-rule` 中性** ⇒ 保持默认 `ed`（最保守）；
# * **`random` 显著更高** ⇒ **推翻 R113** ⇒ 回去查（**不许强行解释**）。
# ⚠ 6 条臂**串行**（每条 ~0.6 GB、~10 min）⇒ 合计 ~1 h；**P33：不并发重臂**。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
LOG=_w2_r581_mn64h.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R114：臂 I 组 —— ed vs random 的多 seed 干净对照 ==="
say "阶段 1：等臂 E/F/G/H 跑完（P33：不并发重臂）…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 720 ] && { say "❌ 等了 6 h ⇒ 退出"; exit 4; }
done
say "阶段 1 完成"

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 100 \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 5 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

m=12
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")

for S in 11 23 37; do
  for VR in ed random; do
    # 臂名：I<seed>_<rule>（rule 用 e/r 缩写，避开 shell 特殊字符）
    R=$([ "$VR" = "ed" ] && echo e || echo r)
    T="I${S}${R}"
    d="$ROOT/dry_$T"
    if [ -d "$d" ]; then
      say "跳过 $T（已存在）"; continue
    fi
    avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
    if [ "$avail" -lt 1500 ]; then
      say "❌ 内存不足（${avail} MB）⇒ 停在 $T"; exit 3
    fi
    say "起 $T：--var-rule $VR --eng-seed $S（cores 8-11）"
    taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag "$T" \
        --laths "$laths" --var-rule "$VR" --eng-seed "$S" \
        > "_w2_r581_mn64_${T}.log" 2>&1
    say "$T 结束 exit=$? Traceback=$(grep -c '^Traceback' "_w2_r581_mn64_${T}.log" || true)"
  done
done

say "── ★ 多 seed 对照表 ──"
$PY - "$ROOT" <<'PYEOF'
import json, os, sys
from collections import Counter
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 96)
print('ed vs random（多 seed）—— 变体数 V 与根数')
print('=' * 96)
print(' %-8s %-9s %-6s %-8s %-8s %s' % ('臂', 'var_rule', 'seed', 'V', '总根数', '每变体'))
print(' ' + '-' * 88)
agg = {}
for s in (11, 23, 37):
    for r, vr in (('e', 'ed'), ('r', 'random')):
        t = 'I%d%s' % (s, r)
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
        V = len(byvar); tot = sum(byvar.values())
        print(' %-8s %-9s %-6d %-8d %-8d %s' % (t, vr, s, V, tot, dict(sorted(byvar.items()))))
        agg.setdefault(vr, []).append((V, tot))
print()
for vr, vals in sorted(agg.items()):
    Vs = [v for v, _ in vals]; Ts = [t for _, t in vals]
    print('  %-8s V = %s（均值 %.2f）；总根数 = %s（均值 %.2f）'
          % (vr, Vs, sum(Vs)/len(Vs), Ts, sum(Ts)/len(Ts)))
print()
print('  ★ 判据：ed 的 V 分布显著高 ⇒ R113 成立；重叠 ⇒ --var-rule 中性（保持默认 ed）')
print('=' * 96)
PYEOF
say "=== R581 MN64H DONE ==="
