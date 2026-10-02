#!/bin/bash
# _r581_mtest.sh --- ★★★ **判决实验**：`nslab_n` 的上限是不是 `m = nv/12`？
#
# ## 假设（R33 从代码推出来的，**可证伪**）
# `nfsv`（同变体⇒新场）只在**同变体的空场**里选 ⇒ **同变体板条数的硬上限 = m = nv/12**。
# 我两臂用 `m=4`，而 `--nuc-block-target 5` ⇒ 要 5 根却只给 4 个场 ⇒ 停在 4 根。
#
# ## 判据（**预先写死**）
# | 臂 | m | 预测的 `nslab_n` 上限 |
# |---|---|---|
# | A | **4**（复现我两臂） | **≤ 4** |
# | B | **12** | **应当突破 4**（若机制健全，应能到 5+） |
# 两个臂**只差 `--m`**，其余逐字相同（单变量）。
# ⚠ 短程（N=64、60 步）**看不到块完全长成**（R22 实测：块在 step 200 才成形）
#   ⇒ 本实验只看**趋势**（`nslab_n` 的**最大值**与 `nfsv_nofield`），**不据此判机制对错**。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mq"
CORES="${R581MQ_CORES:-8-11}"
STEPS="${R581MQ_STEPS:-60}"
BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 1 --snap-every 99999 \
  --pair-every 0 --norm-smooth 0 --nthreads 4 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 5 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis \
  --nfsv-diag 1"

run() {  # run <tag> <m>
  local tag="$1" m="$2"
  # ★ `--m` 在 `_bk_exp.py` 里**有歧义**（`--multi-block`/`--mob-*`）⇒ 必须直接给 `--laths`。
  #   与 `_r581_p2.py:50` 的 `laths()` **逐字相同**：每个变体重复 m 次 ⇒ nv = 12*m
  local laths
  laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")
  local d="$ROOT/dry_$tag"
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
  echo "── 臂 $tag：--m $m （nv = $((12 * m))；--laths 前 20 字符 = ${laths:0:20}…）──"
  taskset -c "$CORES" $PY -u _bk_exp.py $BASE --out "$ROOT" --tag "$tag" --laths "$laths" \
      > "_w2_r581_mq_${tag}.log" 2>&1
  echo "   exit=$? Traceback=$(grep -c '^Traceback' "_w2_r581_mq_${tag}.log" || true)"
}

echo '=== R581-R33 判决实验：`nslab_n` 的上限 == `m = nv/12` ？ ==='
run A 4
run B 12

$PY - "$ROOT" <<'PYEOF'
import json, os, sys
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 88)
print('★ 读数')
print('=' * 88)
for tag, m in (('A', 4), ('B', 12)):
    d = os.path.join(ROOT, 'dry_' + tag)
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        print('  %s：没有 series.csv' % tag); continue
    with open(p) as fh: h = fh.readline().strip().split(',')
    dd = np.genfromtxt(p, delimiter=',', names=True)
    ns = np.atleast_1d(dd['nslab_n']).astype(int) if 'nslab_n' in dd.dtype.names else None
    n2 = np.atleast_1d(dd['nf2']).astype(int) if 'nf2' in dd.dtype.names else None
    vt = np.atleast_1d(dd['Vt']).astype(float) if 'Vt' in dd.dtype.names else None
    print('  %-3s (m=%-3d)  行=%d' % (tag, m, len(ns) if ns is not None else 0))
    if ns is not None:
        print('       nslab_n：%s  ⇒ **max = %d**（预测上限 %d）%s'
              % (list(ns), ns.max(), m, '✅' if ns.max() <= m else '❌ **突破了**'))
    if vt is not None:
        print('       Vt 末值 = %.4f µm³' % vt[-1])
    # nuc_dbg
    q = os.path.join(d, 'nuc_dbg.json')
    if os.path.exists(q):
        j = json.load(open(q, encoding='utf-8'))
        dbg = j.get('dbg', {})
        print('       **`nfsv_nofield` = %s** ；`nfsv_ok` = %s ；`nfsv_diag_occ_sizes` = %s'
              % (dbg.get('nfsv_nofield'), dbg.get('nfsv_ok'),
                 str(dbg.get('nfsv_diag_occ_sizes'))[:80]))
        print('       `T_events` 的 mode 分布 = %s' % j.get('n_events_by_requested_mode'))
    else:
        print('       （无 nuc_dbg.json ⇒ 跑完才写）')
print()
print('=' * 88)
print('★ 判读（**预先写死**）')
print('  · 若 A 停在 ≤4 而 B **突破 4** ⇒ **上限 = m 成立** ⇒ 我上一轮"缺机制"的结论要更正；')
print('  · 若 B 也停在 ≤4 ⇒ 上限不是 m，另有原因（如实登记）。')
print('  ⚠ 短程 60 步看不到块完全长成（R22：块在 step 200 才成形）⇒ 只看**趋势**。')
print('=' * 88)
PYEOF
echo "=== R581 MTEST DONE $(date '+%F %T') ==="
