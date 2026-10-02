#!/bin/bash
# _r581_negctl.sh --- ★★★★★ **四个负对照**（goal 任务(5)：**必须先 FAIL 过，才允许相信门 1 的 PASS**）
#
# ## 判据（**预先写死**）
# | # | 破坏 | **必须** |
# |---|---|---|
# | 1 | φ 只存带内（6Δx） | **FAIL**（共有列出现差异） |
# | 2 | 不恢复 RNG 状态 | **FAIL** |
# | 3 | 不恢复 `_cnt`/`_t_since_reinit` | **FAIL** |
# | 4 | 不恢复 `_nuc['dbg']['ok']` | **允许 PASS，但必须解释** |
#
# ## 基线
# `S3`（一次跑完 16 步）是**真值**；`S2`（从 step 10 续跑）是**正对照**
# ⇒ 正对照必须 PASS（diff=0），四个负对照按上表。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_rsmoke
LOG=_w2_r581_negctl.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

COMMON="--N 64 --dx-nm 62.5 --every 1 --snap-every 100 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4 --steps 16"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

SRC="$ROOT/dry_rs1/ckpt/ckpt_B.npz"     # ★ step 10 那一帧（权威步号在文件内）
if [ ! -f "$SRC" ]; then
  say "❌ 找不到源检查点 $SRC ⇒ 先跑 `_r581_resume_smoke.sh`"
  exit 1
fi
say "源检查点：$SRC（$(stat -c%s "$SRC" | awk '{printf "%.1f MB", $1/1048576}')）"

run_one() {  # $1=tag  $2=ckpt路径
  local tag="$1" ck="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  timeout 1800 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $COMMON --resume "$ck" \
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_neg_${tag}.log" 2>&1
  local rc=$?
  printf '    %-10s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$rc" \
    "$(grep -c '^Traceback' "_w2_r581_neg_${tag}.log" || echo 0)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say '════ ⓪ 正对照（不破坏）—— **必须 PASS** ════'
run_one nc_ok "$SRC"
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_nc_ok/series.csv" "$ROOT/dry_rs3/series.csv" step 2>&1 \
  | grep -E '差异字段数|共有列逐位一致' | sed 's/^/    /'

for spec in "phi_band_only:nc_neg1:1:必须FAIL" \
            "no_rng:nc_neg2:1:必须FAIL" \
            "no_reinit_clock:nc_neg3:1:必须FAIL" \
            "no_dbg_ok:nc_neg4:0:允许PASS但须解释"; do
  IFS=':' read -r kind tag must note <<< "$spec"
  say "════ ${tag}：破坏=$kind（$note）════"
  BAD="$ROOT/dry_negctl_${kind}.npz"
  $PY _r581_ckpt_negctl.py "$SRC" "$BAD" "$kind" 6 2>&1 | sed 's/^/  /'
  run_one "$tag" "$BAD"
  taskset -c 16-19 $PY _r581_ckpt_cmp.py \
    "$ROOT/dry_${tag}/series.csv" "$ROOT/dry_rs3/series.csv" step 2>&1 \
    | grep -E '差异字段数|共有列逐位一致|有差异的列|^    [A-Za-z_]+ +[0-9]+ 处' | head -8 | sed 's/^/    /'
done

say '════ 汇总 ════'
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import csv, os, sys
import numpy as np
sys.path.insert(0, '.')
from _r581_ckpt_cmp import cell_bits, load
ROOT = sys.argv[1]
REF = os.path.join(ROOT, 'dry_rs3', 'series.csv')
rr = load(REF)
mref = {r['step']: r for r in rr}
cols = [c for c in rr[0] if c != 'wall_s']
ARMS = [('nc_ok', '正对照（不破坏）', 'PASS'),
        ('nc_neg1', '负1: φ 只存带内', 'FAIL'),
        ('nc_neg2', '负2: 不恢 RNG', 'FAIL'),
        ('nc_neg3', '负3: 不恢 _cnt/_t_since_reinit', 'FAIL'),
        ('nc_neg4', '负4: 不恢 dbg[ok]', 'PASS(须解释)')]
print()
print('  %-8s %-30s %-10s %-9s %s' % ('臂', '破坏项', '判据要求', '实测差异', '判定'))
print('  ' + '-' * 88)
for tag, name, want in ARMS:
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        print('  %-8s %-30s %-10s %s' % (tag, name, want, '（缺失）'))
        continue
    rows = load(p)
    mr = {r['step']: r for r in rows}
    common = sorted(set(mr) & set(mref), key=lambda x: int(x))
    nd = 0
    badcols = {}
    for k in common:
        for c in cols:
            if cell_bits(mr[k].get(c)) != cell_bits(mref[k].get(c)):
                nd += 1
                badcols[c] = badcols.get(c, 0) + 1
    got = 'PASS' if nd == 0 else 'FAIL'
    ok = (got == want) or (want.startswith('PASS') and got == 'PASS')
    print('  %-8s %-30s %-10s %-9s %s%s' %
          (tag, name, want, ('%d 处' % nd) if nd else '**0（逐位一致）**',
           '✅' if ok else '❌',
           ('  ← %s' % dict(sorted(badcols.items(), key=lambda x: -x[1])[:3]))
           if badcols else ''))
print()
print('  ★ 读法：**门 1 的 PASS 只有在负对照 1–3 都 FAIL 之后才算数**（goal 硬要求）。')
print('     负 4 允许 PASS ⇒ 但**必须解释**（例：这一轮没走 attach 通道 ⇒ `ok` 的奇偶没被读到）。')
PYEOF
say '=== NEGCTL DONE ==='
