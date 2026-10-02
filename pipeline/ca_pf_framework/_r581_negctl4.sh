#!/bin/bash
# _r581_negctl4.sh --- ★★★★★★ **针对性把负 3 逼出来**：让 `_cnt` 真的成为决定性触发
#
# ## 机制（第 3 版实测出来的）
# `reinitialize()` 的触发是**两条或**（`windowB_surface.py`）：
#   ① `_cnt % reinit_every == 0`（**步数**节拍）
#   ② `_t_since_reinit >= reinit_dt`（**时间**节拍）
# 第 3 版用了 `--reinit-dt 1e-8`（`dt ≈ 2.7e-8`）⇒ **② 每步都命中** ⇒
# **① 永远不是决定性的** ⇒ 把 `_cnt` 归零**没有任何效果** ⇒ 负 3 无分辨力。
#
# ## 本版怎么让 ① 成为决定性
# * **`--reinit-dt 1e-6`**（远大于 dt ⇒ **② 在窗口内不触发**）⇒ **只有 ① 能触发**
# * **`--reinit-every 3`**（若该开关存在；否则用默认值）⇒ `_cnt` 归零 ⇒ **触发步错开**
# * **窗口 0 → 12 步**（够跨过若干 `_cnt` 周期）
#
# ## 判据（**预先写死**）
# | 臂 | 必须 |
# |---|---|
# | S2 正对照 | **PASS**（diff=0） |
# | 负3 不恢 `_cnt`/`_t_since_reinit` | **★ FAIL** |
# ## 分辨力**先验**：窗口内必须有 reinit 发生（数日志），否则停。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_nc4
LOG=_w2_r581_nc4.log
STEPS=12
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CFG="--N 64 --dx-nm 62.5 --every 1 --snap-every 200 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-6 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

run() {
  local tag="$1" extra="$2" st="$3"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $CFG --steps "$st" $extra \
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_nc4_${tag}.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_nc4_${tag}.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say '=== ① S1：只写 step 0 那一帧 ==='
run nc4_s1 "--ckpt-every 1 --ckpt-keep 2" 0
say '=== ② S3：连续跑 '"$STEPS"' 步（真值）==='
run nc4_s3 "" "$STEPS"

say '=== ③ 分辨力先验：窗口内 reinit 次数（用 awk，避开 grep -c 多行陷阱）==='
REI=$(awk 'tolower($0) ~ /reinit/' "_w2_r581_nc4_nc4_s3.log" 2>/dev/null | wc -l)
REI_W=$(awk "tolower(\$0) ~ /reinit/ && / step ([1-9]|1[0-2])/" \
        "_w2_r581_nc4_nc4_s3.log" 2>/dev/null | wc -l)
say "  含 reinit 行数 = $REI ；窗口内（step 1–$STEPS）= $REI_W"
say '  ── reinit 的样本行 ──'
grep -iE 'reinit' "_w2_r581_nc4_nc4_s3.log" 2>/dev/null | head -5 | cut -c1-104 | sed 's/^/    /'
if [ "$REI" -lt 1 ]; then
  say '  ❌ 窗口内没有 reinit ⇒ 负 3 仍无分辨力 ⇒ 停（不许硬测）'
  exit 2
fi

say "=== ④ S2：正对照（step 0 → $STEPS）==="
run nc4_s2 "--resume $ROOT/dry_nc4_s1/ckpt" "$STEPS"
grep -E '自动选|检查点 step=|驱动层已回填' "_w2_r581_nc4_nc4_s2.log" 2>/dev/null | sed 's/^/    /'

say '=== ⑤ 负 3：不恢 `_cnt`/`_t_since_reinit` ==='
REAL=$($PY - <<'PYEOF'
import os, numpy as np
d = '_exp/_bk_nc4/dry_nc4_s1/ckpt'
best = None
for f in sorted(os.listdir(d)):
    if f.startswith('ckpt') and f.endswith('.npz'):
        with np.load(os.path.join(d, f), allow_pickle=False) as z:
            s = int(np.asarray(z['step']).item())
        if best is None or s > best[0]:
            best = (s, os.path.join(d, f))
print(best[1] if best else '')
PYEOF
)
BAD="$ROOT/dry_neg_no_reinit_clock.npz"
$PY _r581_ckpt_negctl.py "$REAL" "$BAD" no_reinit_clock 6 2>&1 | sed 's/^/  /'
run nc4_n3 "--resume $BAD" "$STEPS"

say '════ 汇总 ════'
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, sys
sys.path.insert(0, '.')
from _r581_ckpt_cmp import cell_bits, load
ROOT = sys.argv[1]
ref = load(os.path.join(ROOT, 'dry_nc4_s3', 'series.csv'))
mref = {r['step']: r for r in ref}
cols = [c for c in ref[0] if c != 'wall_s']
print()
print('  %-9s %-34s %-12s %-10s %s' % ('臂', '说明', '判据', '实测差异', '判定'))
print('  ' + '-' * 90)
for tag, name, want in (('nc4_s2', '正对照（不破坏）', 'PASS'),
                        ('nc4_n3', '负3 不恢 _cnt/_t_since_reinit', 'FAIL')):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        print('  %-9s %-34s %-12s %s' % (tag, name, want, '（缺失）'))
        continue
    rows = load(p)
    mr = {r['step']: r for r in rows}
    common = sorted(set(mr) & set(mref), key=int)
    nd = 0
    bad = {}
    for k in common:
        for c in cols:
            if cell_bits(mr[k].get(c)) != cell_bits(mref[k].get(c)):
                nd += 1
                bad[c] = bad.get(c, 0) + 1
    got = 'PASS' if nd == 0 else 'FAIL'
    print('  %-9s %-34s %-12s %-10s %s %s' %
          (tag, name, want, ('%d 处' % nd) if nd else '**0**',
           '✅' if got == want else '❌',
           dict(sorted(bad.items(), key=lambda x: -x[1])[:4]) if bad else ''))
print()
print('  ★ 读法：**若负 3 这次 FAIL，就证明 `_cnt`/`_t_since_reinit` 那一项必要**')
print('     （第 3 版之所以不 FAIL，是 `--reinit-dt 1e-8` 让**时间触发**每步命中，')
print('      把 `_cnt` 那条路**屏蔽**掉了 —— 那不是"不需要存"，是"没测到"）')
PYEOF
say '=== NC4 DONE ==='
