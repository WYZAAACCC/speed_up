#!/bin/bash
# _r581_mn64e.sh --- ★★★★★ **臂 F：C5 的**五旋钮全开**配方（直测 C5）**
#
# ## R92 的决定性发现（代码逐字，`_bk_exp.py:2004-2010`）
#     _tgt = min(_Bt * _n_blk, nv)        # ← ★ 总根数目标 = B × n_blk
#   其中 `_Bt` = `--nuc-block-target`（**CLI 旋钮**）、
#        `_n_blk` = `CL.alpha_km_n_lath(T, α)` = **每块根数**（C-2 律；`:651-654` 逐字：
#        「C-2 的 `n` 是**每块**根数，不是全盒总数」）
#   ⇒ **总根数 ≈ `_tgt` = `B × n_blk`**（实测：`B=5`、`n_blk=3` ⇒ `_tgt=15` == `n_target_final` ✓）
#
# ## ⇒ C5（220–450 根）的**五旋钮**
# | # | 旋钮 | 现值 | **C5 需要** |
# |---|---|---|---|
# | 1 | **`--nuc-block-target B`** | 5 | **≥ 74**（`n_blk=3` 下 ⇒ `_tgt ≥ 222`）★ 主杠杆 |
# | 2 | `--m`（每变体场数） | 4/12 | **20**（`nv=240` ⇒ 容量够） |
# | 3 | `--var-rule` | `ed` | **`random`**（`V→12`，摊开名额） |
# | 4 | `--nuc-overlap-nm`（S4） | 0 | **62.5**（打开 `stack` 通道） |
# | 5 | `--nuc-fresh-every K` | 自动 =5 | **5**（每 5 事件建 1 新块） |
#
# ## 本臂 = **五旋钮全开**（N=64 上，内存 ~600 MB）
# **判据（预先写死）**：
# * **总根数进入 220–450** ⇒ **C5 在 N=64 上达成** ⇒ 按 R53 的账外推到 N=160；
# * **总根数 ≈ `B × n_blk`（≈222）** ⇒ **R92 的公式成立**；
# * **总根数仍 ≪ 220** ⇒ **另有一层没识别出的约束** ⇒ 继续查。
# ⚠ **本臂不替代 N=160**；它只回答"**这个配方能不能到 220–450**"。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
LOG=_w2_r581_mn64e.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R93：臂 F —— C5 五旋钮全开（m=20 + B=74 + random + S4 + K=5）==="
say "阶段 1：等臂 C/D/E 跑完…"
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
d="$ROOT/dry_F"
[ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
say "起臂 F：--m 20 --nuc-block-target 74 --var-rule random（nv=240）cores 8-11"
taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag F --laths "$laths" \
    --nuc-block-target 74 --var-rule random > _w2_r581_mn64_F.log 2>&1
say "臂 F 结束 exit=$? Traceback=$(grep -c '^Traceback' _w2_r581_mn64_F.log || true)"

say "── 六臂对照（A–F）+ C5 判决 ──"
$PY - "$ROOT" <<'PYEOF'
import json, os, sys
from collections import Counter
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 100)
print('C5 直测：总根数 vs 220–450')
print('=' * 100)
print(' %-4s %-6s %-10s %-10s %-12s %-10s %s'
      % ('臂', 'm', 'B', 'n_target', 'var_rule', '总根数', 'V'))
print(' ' + '-' * 96)
for t in ['A', 'B', 'C', 'D', 'E', 'F']:
    d = os.path.join(ROOT, 'dry_' + t)
    if not os.path.isdir(d):
        continue
    p = os.path.join(d, 'nuc_dbg.json')
    m = B = nt = vr = '?'
    if os.path.exists(p):
        j = json.load(open(p, encoding='utf-8'))
        cfg = j.get('nuc_cfg', {})
        vg = cfg.get('vgroup', {})
        m = len(vg) // 12 if vg else '?'
        B = cfg.get('n_target', '?')
        B = j.get('n_target_final', '?')
        vr = cfg.get('var_rule', '?')
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    tot = V = '?'
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
            tot = sum(byvar.values()); V = len(byvar)
    print(' %-4s %-6s %-10s %-10s %-12s %-10s %s' % (t, m, B, nt, vr, tot, V))
print()
print('  ★ 判据：总根数进 **220–450** ⇒ C5 达成；≈ `B×n_blk`=222 ⇒ R92 公式成立')
print('=' * 100)
PYEOF
say "=== R581 MN64E DONE ==="
