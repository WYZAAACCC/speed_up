#!/bin/bash
# _r581_negctl2.sh --- ★★★★★ **有分辨力的**四个负对照（第三轮重做）
#
# ## 为什么要重做（上一轮的实测教训）
# 上一轮的配置里：**全部 4 次形核都在 step 1**（检查点在 step 10 之前），
# 而窗口只有 **6 步**（11–16）⇒ **RNG 一次都没被消费、reinit 一次都没发生**
# ⇒ 负对照 2/3 **没有分辨力**（不是"那两项不重要"）—— 正是 goal 硬要求的
# 「**负对照必须在生产参数上有效**」要防的事。
#
# ## 这一轮怎么造分辨力
# | 手段 | 为什么 |
# |---|---|
# | **`--nuc-block-target 20`** | 形核**分散到多步**（不再一次性在 step 1 全出来）⇒ 窗口内真的消耗 RNG |
# | **`--reinit-dt 1e-8`** | `dt≈2.7e-8` ⇒ **几乎每步都触发 reinit** ⇒ `_cnt`/`_t_since_reinit` 真的被读到 |
# | **窗口 10 → 30 步**（20 步） | 给上述两者留出发生的机会 |
#
# ## 判据（**预先写死**）
# | # | 破坏 | 必须 |
# |---|---|---|
# | ⓪ | 正对照（不破坏） | **PASS**（否则一切无意义） |
# | 1 | φ 只存带内 | **FAIL** |
# | 2 | 不恢 RNG | **FAIL**（**这一轮必须真 FAIL**） |
# | 3 | 不恢 `_cnt`/`_t_since_reinit` | **FAIL**（**这一轮必须真 FAIL**） |
# | 4 | 不恢 `dbg[ok]` | 允许 PASS，但须解释 |
#
# ## 分辨力**先验**（先证明，再测）
# 必须在连续跑（S3）的日志里数出：**step>10 之后的形核次数**与 **reinit 次数**
# ⇒ **两者都 >0 才允许开始测负对照**（否则又是无分辨力）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_nc2
LOG=_w2_r581_nc2.log
STEPS=30
CUT=10
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CFG="--N 64 --dx-nm 62.5 --every 1 --snap-every 200 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 20 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-8 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

run() {  # $1=tag  $2=额外参数
  local tag="$1" extra="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $CFG --steps "$STEPS" $extra \
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_nc2_${tag}.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_nc2_${tag}.log" || echo 0)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say "=== ① S3：**连续跑** $STEPS 步（真值）==="
run nc2_s3 ""

say '=== ② ★ **分辨力先验**：窗口（step>10）内有没有形核 / reinit ==='
NUC_IN=$(grep -cE 'athermal 形核.*@ step (1[1-9]|2[0-9]|30)' "_w2_r581_nc2_nc2_s3.log" 2>/dev/null || echo 0)
NUC_ALL=$(grep -cE 'athermal 形核.*@ step ' "_w2_r581_nc2_nc2_s3.log" 2>/dev/null || echo 0)
REI=$(grep -ciE 'reinit' "_w2_r581_nc2_nc2_s3.log" 2>/dev/null || echo 0)
say "  形核总行数 = $NUC_ALL ；**窗口内（step>10）= $NUC_IN** ；含 reinit 的行 = $REI"
grep -oE 'athermal 形核.*@ step [0-9]+' "_w2_r581_nc2_nc2_s3.log" 2>/dev/null \
  | grep -oE 'step [0-9]+' | sort | uniq -c | head -12 | sed 's/^/    /'
if [ "$NUC_IN" -eq 0 ]; then
  say '  ❌ **窗口内没有形核 ⇒ 负对照 2 仍无分辨力** ⇒ 停，回去调配置'
  exit 2
fi
say '  ✅ 窗口内有形核 ⇒ 负对照 2 有分辨力'

say '=== ③ S1：跑到 step 10 并存检查点 ==='
run nc2_s1 "--ckpt-every $CUT --ckpt-keep 2"
SRC="$ROOT/dry_nc2_s1/ckpt"
ls -la "$SRC" 2>/dev/null | sed 's/^/    /'

say '=== ④ S2：**正对照**——从 step 10 续跑到 30（必须 PASS）==='
run nc2_s2 "--resume $SRC"
grep -E '自动选|检查点 step=|P0 已回填|驱动层已回填' "_w2_r581_nc2_nc2_s2.log" 2>/dev/null | sed 's/^/    /'

say '=== ⑤ 四个负对照 ==='
# ★ 源帧 = step 10 那一帧（按内部 step 选，别靠文件名）
REAL=$($PY - <<'PYEOF'
import os, numpy as np
d = '_exp/_bk_nc2/dry_nc2_s1/ckpt'
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
for spec in "phi_band_only:nc2_n1" "no_rng:nc2_n2" "no_reinit_clock:nc2_n3" "no_dbg_ok:nc2_n4"; do
  IFS=':' read -r kind tag <<< "$spec"
  BAD="$ROOT/dry_neg_${kind}.npz"
  $PY _r581_ckpt_negctl.py "$REAL" "$BAD" "$kind" 6 2>&1 | sed 's/^/  /'
  run "$tag" "--resume $BAD"
done

say '════ 汇总 ════'
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, sys
sys.path.insert(0, '.')
from _r581_ckpt_cmp import cell_bits, load
ROOT = sys.argv[1]
ref = load(os.path.join(ROOT, 'dry_nc2_s3', 'series.csv'))
mref = {r['step']: r for r in ref}
cols = [c for c in ref[0] if c != 'wall_s']
ARMS = [('nc2_s2', '正对照', 'PASS'), ('nc2_n1', '负1 φ只存带内', 'FAIL'),
        ('nc2_n2', '负2 不恢RNG', 'FAIL'), ('nc2_n3', '负3 不恢_cnt/_t_since_reinit', 'FAIL'),
        ('nc2_n4', '负4 不恢dbg[ok]', 'PASS-OR-EXPLAIN')]
print()
print('  %-9s %-30s %-16s %-11s %s' % ('臂', '破坏项', '判据要求', '实测差异', '判定'))
print('  ' + '-' * 92)
for tag, name, want in ARMS:
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        print('  %-9s %-30s %-16s %s' % (tag, name, want, '（缺失）'))
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
    print('  %-9s %-30s %-16s %-11s %s %s' %
          (tag, name, want, ('%d 处' % nd) if nd else '**0**',
           '✅' if ok else '❌',
           dict(sorted(bad.items(), key=lambda x: -x[1])[:3]) if bad else ''))
print()
print('  ★ **门 1 的 PASS 只有在负 1–3 都 FAIL 之后才算数**')
print('  ★ 负 4 允许 PASS ⇒ 必须解释（若 PASS：说明这一轮 `ok` 的奇偶没被读到）')
PYEOF
say '=== NC2 DONE ==='
