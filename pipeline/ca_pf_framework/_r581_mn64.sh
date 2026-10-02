#!/bin/bash
# _r581_mn64.sh --- ★★★★ **`m` 假说的 N=64 快速判决**（与 N=160 的长跑**并行**，不抢内存）
#
# ## 为什么可以放到 N=64 上做
# `m` 限的是**同一变体有几个场**（`nfsv` 只能在同变体的空场里选）——
# 那是**场配额**，**与盒子大小 N 无关**。
# ⇒ **"同变体 max 是否随 `m` 上升"这个判据，在 N=64 上就能判**，而且**内存是零头**：
#   N=64 ⇒ `CELL = 64³ = 262144`；`nv=144` ⇒ `9.000 × 144 × 262144 B = **340 MB**`。
#   ⇒ **可以在 cores 8-11 上跑，完全不影响 0-3/4-7 的两条 N=160 长跑**（P23 的内存闸）。
#
# ## 判据（**预先写死**）
# | 臂 | `m` | 预期「同变体 max」 |
# |---|---|---|
# | A | **4**（对照） | **≤ 4** |
# | B | **12** | **应当 > 4，趋向 12** |
# 两臂**只差 `--m`**，其余逐字相同。
# ⚠ 短程（250 步）—— 但要跟 R58 的 N=160/m=4 短程判决（`m=4 ⇒ max 4`）**同口径**。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 100 \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 5 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

run() {  # run <tag> <m> <cores>
  local tag="$1" m="$2" cores="$3"
  local laths
  laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")
  local d="$ROOT/dry_$tag"
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
  echo "── $tag：--m $m（nv=$((12*m))）cores $cores ──"
  taskset -c "$cores" $PY -u _bk_exp.py $BASE --out "$ROOT" --tag "$tag" --laths "$laths" \
      > "_w2_r581_mn64_${tag}.log" 2>&1
  echo "   exit=$? Traceback=$(grep -c '^Traceback' "_w2_r581_mn64_${tag}.log" || true)"
}

echo '=== R581-R60：`m` 假说的 N=64 快速判决（与 N=160 长跑并行）==='
run A 4  8-9
run B 12 10-11

$PY - "$ROOT" <<'PYEOF'
import json, os, sys
from collections import Counter
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 96)
print('★ 判决：`m` 是否真是"同变体板条数"的上限？')
print('=' * 96)
for tag, m in (('A', 4), ('B', 12)):
    d = os.path.join(ROOT, 'dry_' + tag)
    p = os.path.join(d, 'nuc_dbg.json')
    if not os.path.exists(p):
        print('  %-3s ❌ 无 nuc_dbg.json' % tag); continue
    j = json.load(open(p, encoding='utf-8'))
    cfg = j.get('nuc_cfg', {})
    vg = {int(a): int(b) for a, b in cfg.get('vgroup', {}).items()}
    cnt = Counter(vg.values())
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    print()
    print('  ── 臂 %s：--m %d（nv=%d）──' % (tag, m, len(vg)))
    print('     每变体场数：%s' % dict(sorted(cnt.items())))
    for s in snaps:
        z = np.load(os.path.join(d, s))
        if 'region' not in z or 'vmap_keys' not in z:
            continue
        reg = z['region']
        vk = [int(x) for x in np.asarray(z['vmap_keys']).ravel()]
        vv = [int(x) for x in np.asarray(z['vmap_vals']).ravel()]
        vm = dict(zip(vk, vv))
        byvar = Counter()
        for f in np.unique(reg):
            f = int(f)
            if f > 0:
                byvar[vm.get(f, -1)] += 1
        mx = max(byvar.values()) if byvar else 0
        print('     %s (step %d)：**同变体 max = %d**  每变体：%s'
              % (s, int(z['step']), mx, dict(sorted(byvar.items()))))
print()
print('=' * 96)
print('★ 判读（**预先写死**）')
print('  · 臂 B（m=12）的「同变体 max」**> 4** ⇒ **`m` 就是上限** ⇒ 按 R53 上 `m=20`/`38`')
print('  · 臂 B 仍 **= 4** ⇒ **上限不是 `m`**，必须另查（第五条自我更正）')
print('  ⚠ 短程 250 步；与 R58 的 N=160/m=4 判决（max=4）**同口径**')
print('=' * 96)
PYEOF
echo "=== R581 MN64 DONE $(date '+%F %T') ==="
