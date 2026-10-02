#!/bin/bash
# _r581_mn64f.sh --- ★★★★★ **臂 G：`B=150`（R94 的达成率修正）+ `m=20` + `random` + S4**
#
# ## 为什么需要臂 G（R94 的实测）
# 盘上的 N=160 长跑给出**两个硬数**：
#   * `p2_b5`：`_tgt` = **25**、**实测事件只有 10** ⇒ **达成率 40%**
#   * `p2_b3`：`_tgt` = **15**、**实测事件只有 5**  ⇒ **达成率 33%**
# **⇒ `_tgt = B × n_blk(T)` 只是**目标**；**实际根数 = 目标 × 达成率（33–40%）**。**
# ⇒ 要**实际** 220–450 根，**目标**必须 ≈ **550–1100**：
#     在 `T_end` 的 `n_blk=5` 下 ⇒ **`B ≥ 110`**（**不是 R92 说的 74，也不是 R94 修正的 44**）。
#
# ## 本臂 = 臂 F 的**单变量**延续
# | 臂 | `m` | `B` | `--var-rule` | S4 | 测的是 |
# |---|---|---|---|---|---|
# | F | 20 | **74**  | random | ✅ | `_tgt = 370` ⇒ 若达成率 40% ⇒ **实际 ~148**（**可能不够**） |
# | **G** | 20 | **150** | random | ✅ | **`_tgt = 750` ⇒ 实际 ~300 ⇒ 应进 220–450** |
# **⇒ F 与 G 只差 `B` ⇒ **直接量出"达成率"**（这正是 R94 的最不确定处）。**
#
# ## 判据（**预先写死**）
# * **臂 G 实际根数进入 220–450** ⇒ **C5 达成**（并给出达成率 = 实际/`_tgt`）；
# * **臂 G 实际根数 ≈ 臂 F 的 2×** ⇒ **确认"实际 ∝ `_tgt`"** ⇒ 处方闭环；
# * **臂 G 实际根数不随 `B` 涨** ⇒ **达成率不是常数，而是被**别的**东西卡住** ⇒ 另查。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
LOG=_w2_r581_mn64f.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R95：臂 G —— B=150（R94 达成率修正后的配方）==="
say "阶段 1：等臂 C/D/E/F 跑完…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 600 ] && { say "❌ 等了 5 h ⇒ 退出"; exit 4; }
done
say "阶段 1 完成"

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB"
[ "$avail" -lt 1500 ] && { say "❌ 内存不足"; exit 3; }

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 100 \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

m=20
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")
d="$ROOT/dry_G"
[ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
say "起臂 G：--m 20 --nuc-block-target 150 --var-rule random（nv=240）cores 8-11"
taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag G --laths "$laths" \
    --nuc-block-target 150 --var-rule random > _w2_r581_mn64_G.log 2>&1
say "臂 G 结束 exit=$? Traceback=$(grep -c '^Traceback' _w2_r581_mn64_G.log || true)"

say "── ★ F vs G：达成率直测 ──"
$PY - "$ROOT" <<'PYEOF'
import json, os, sys
from collections import Counter
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 100)
print('★ F vs G：`_tgt` 与实际根数（= 达成率直测）')
print('=' * 100)
print(' %-4s %-6s %-10s %-10s %-12s %-10s %s'
      % ('臂', 'm', 'B(cli)', 'n_target', 'events', '实际根数', '达成率'))
print(' ' + '-' * 96)
BCLI = {'F': 74, 'G': 150}
for t in ['E', 'F', 'G']:
    d = os.path.join(ROOT, 'dry_' + t)
    if not os.path.isdir(d):
        continue
    p = os.path.join(d, 'nuc_dbg.json')
    m = nt = ev = '?'
    if os.path.exists(p):
        j = json.load(open(p, encoding='utf-8'))
        vg = j.get('nuc_cfg', {}).get('vgroup', {})
        m = len(vg) // 12 if vg else '?'
        nt = j.get('n_target_final', '?')
        ev = j.get('n_athermal_ev', '?')
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    tot = '?'
    if snaps:
        z = np.load(os.path.join(d, snaps[-1]))
        if 'region' in z and 'vmap_keys' in z:
            reg = z['region']
            vm = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                          [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
            byvar = Counter()
            for f in np.unique(reg):
                f = int(f)
                if f > 0:
                    byvar[vm.get(f, -1)] += 1
            tot = sum(byvar.values())
    rate = ('%.0f%%' % (100 * tot / nt)) if (isinstance(tot, int) and isinstance(nt, int) and nt) else '?'
    print(' %-4s %-6s %-10s %-10s %-12s %-10s %s'
          % (t, m, BCLI.get(t, '?'), nt, ev, tot, rate))
print()
print('  ★ 判据：G 实际进 220–450 ⇒ C5 达成；G ≈ 2×F ⇒ 确认"实际 ∝ _tgt"')
print('=' * 100)
PYEOF
say "=== R581 MN64F DONE ==="
