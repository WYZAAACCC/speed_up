#!/bin/bash
# _r581_negctl3.sh --- ★★★★★★ **有分辨力的**负对照（第三轮·**最终版**）
#
# ## 前两版为什么不行（**实测教训，必须留档**）
# | 版本 | 检查点 | 窗口 | 窗口内形核 | 窗口内 reinit | 结论 |
# |---|---|---|---|---|---|
# | 第 1 版 | step 10 | 11–16 | **0** | **0** | 负 2/负 3 **无分辨力** |
# | 第 2 版 | step 10 | 11–30 | **0**（`--nuc-block-target 20` 也没用） | 111 行 ✓ | 负 3 有、负 2 **仍无** |
#
# **★ 根因（第 2 版实测）**：`grep -oE …@ step N | uniq -c` ⇒ **`15 step 1`**
# —— **athermal 律把**全部**块在 **step 1** 一次性释放**（"累计 2/5…5/5" 同一步）
# ⇒ **RNG 只在 step 1 被消费** ⇒ **检查点必须在 step 0**，窗口才会包含它。
#
# ## 本版设计（**便宜 + 真有分辨力**）
# * **S1 = `--steps 0 --ckpt-every 1`** ⇒ **只写 step 0 那一帧**（几秒）
# * **S3 = 连续跑 6 步**（真值，约 3 min）
# * **S2 = 从 step 0 续跑到 6** ⇒ 窗口 = **steps 1..6** ⇒ **含 step 1 的形核** ✓
# * **`--reinit-dt 1e-8`** ⇒ 几乎每步 reinit ⇒ `_cnt`/`_t_since_reinit` 有分辨力 ✓
#
# ## 判据（**预先写死**）
# | # | 破坏 | 必须 |
# |---|---|---|
# | ⓪ | 正对照 | **PASS** |
# | 1 | φ 只存带内 | **FAIL** |
# | 2 | **不恢 RNG** | **★ FAIL（本版必须有分辨力）** |
# | 3 | **不恢 `_cnt`/`_t_since_reinit`** | **★ FAIL** |
# | 4 | 不恢 `dbg[ok]` | 允许 PASS，但须解释 |
#
# ## ★ 分辨力**先验**（**修了上一版的 grep 多行 bug**）
# 用 `grep -c` 取数时必须 `| head -1`（它可能返回多行 ⇒ `[ -eq ]` 静默失效，
# 上一版就是因此**误报"✅ 有分辨力"**）。本版用 `awk` 直接求和。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_nc3
LOG=_w2_r581_nc3.log
STEPS=6
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CFG="--N 64 --dx-nm 62.5 --every 1 --snap-every 200 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-8 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

run() {
  local tag="$1" extra="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $CFG --steps "$3" $extra \
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_nc3_${tag}.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_nc3_${tag}.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say "=== ① S1：**只写 step 0 那一帧**（--steps 0）==="
run nc3_s1 "--ckpt-every 1 --ckpt-keep 2" 0
ls -la "$ROOT/dry_nc3_s1/ckpt/" 2>/dev/null | sed 's/^/    /'

say "=== ② S3：**连续跑** $STEPS 步（真值）==="
run nc3_s3 "" "$STEPS"

say '=== ③ ★ **分辨力先验**（用 awk 求和，避开 grep -c 多行陷阱）==='
NUC_IN=$(awk '/athermal 形核/ && /@ step [1-9]/' "_w2_r581_nc3_nc3_s3.log" 2>/dev/null | wc -l)
REI=$(awk 'tolower($0) ~ /reinit/' "_w2_r581_nc3_nc3_s3.log" 2>/dev/null | wc -l)
say "  窗口（step ≥ 1）内的形核行数 = **$NUC_IN**；含 reinit 的行 = **$REI**"
say '  ── 形核的步号分布 ──'
grep -oE '@ step [0-9]+' "_w2_r581_nc3_nc3_s3.log" 2>/dev/null | sort | uniq -c | head -8 | sed 's/^/    /'
if [ "$NUC_IN" -lt 1 ] || [ "$REI" -lt 1 ]; then
  say "  ❌ **分辨力不足**（形核 $NUC_IN / reinit $REI）⇒ **停，回去调配置**（不许硬测）"
  exit 2
fi
say '  ✅ **形核与 reinit 都在窗口内** ⇒ 负 2/负 3 **有分辨力**'

say "=== ④ S2：**正对照**——从 step 0 续跑到 $STEPS ==="
run nc3_s2 "--resume $ROOT/dry_nc3_s1/ckpt" "$STEPS"
grep -E '自动选|检查点 step=|P0 已回填|驱动层已回填|版本哈希' \
  "_w2_r581_nc3_nc3_s2.log" 2>/dev/null | sed 's/^/    /'

say '=== ⑤ 四个负对照 ==='
REAL=$($PY - <<'PYEOF'
import os, numpy as np
d = '_exp/_bk_nc3/dry_nc3_s1/ckpt'
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
say "  源帧（step 最大）= $REAL"
for spec in "phi_band_only:nc3_n1" "no_rng:nc3_n2" "no_reinit_clock:nc3_n3" "no_dbg_ok:nc3_n4"; do
  IFS=':' read -r kind tag <<< "$spec"
  BAD="$ROOT/dry_neg_${kind}.npz"
  $PY _r581_ckpt_negctl.py "$REAL" "$BAD" "$kind" 6 2>&1 | sed 's/^/  /'
  run "$tag" "--resume $BAD" "$STEPS"
done

say '════ 汇总 ════'
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, sys
sys.path.insert(0, '.')
from _r581_ckpt_cmp import cell_bits, load
ROOT = sys.argv[1]
ref = load(os.path.join(ROOT, 'dry_nc3_s3', 'series.csv'))
mref = {r['step']: r for r in ref}
cols = [c for c in ref[0] if c != 'wall_s']
ARMS = [('nc3_s2', '正对照', 'PASS'), ('nc3_n1', '负1 φ只存带内', 'FAIL'),
        ('nc3_n2', '★ 负2 不恢RNG', 'FAIL'), ('nc3_n3', '★ 负3 不恢_cnt/_t_since_reinit', 'FAIL'),
        ('nc3_n4', '负4 不恢dbg[ok]', 'PASS-OR-EXPLAIN')]
print()
print('  %-9s %-32s %-16s %-10s %s' % ('臂', '破坏项', '判据要求', '实测差异', '判定'))
print('  ' + '-' * 94)
for tag, name, want in ARMS:
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        print('  %-9s %-32s %-16s %s' % (tag, name, want, '（缺失）'))
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
    ok = (got == want) or want.startswith('PASS')
    print('  %-9s %-32s %-16s %-10s %s %s' %
          (tag, name, want, ('%d 处' % nd) if nd else '**0**',
           '✅' if ok else '❌',
           dict(sorted(bad.items(), key=lambda x: -x[1])[:3]) if bad else ''))
print()
print('  ★ **门 1 的 PASS 只有在负 1–3 都 FAIL 之后才算数**')
print('  ★ 负 4 允许 PASS ⇒ 必须解释')
PYEOF
say '=== NC3 DONE ==='
