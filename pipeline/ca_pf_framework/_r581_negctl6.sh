#!/bin/bash
# _r581_negctl6.sh --- ★★★★★ **负 4 的修正版**：`dbg['ok']` 要**翻转奇偶**，不是归零
#
# ## 上一轮为什么拿 0 处差异（我的**判据设计缺陷**）
# `dbg['ok']` 只被**一处**读、而且**只读它的奇偶**：
#   `windowB_surface.py:2534`：`_sides = ((1.0, -1.0) if (_dbg.get('ok', 0) % 2 == 0) else (-1.0, 1.0))`
# 上一轮的破坏是**归零** —— 而那一轮 `ok` 本来就是 **4（偶数）** ⇒ **奇偶没变** ⇒ `_sides` 相同
# ⇒ **测不出差异**。**⇒ 那是"没测到"，不是"不重要"**（P47）。
#
# ## 本版
# * **破坏模式 `dbg_ok_odd`**：把 `nuc_ok` 置成**与原来奇偶相反**的值
# * **检查点在 step 0**（`ok`=0）⇒ 破坏后 `ok`=1 ⇒ **奇偶翻转**
# * **窗口 0 → 6**，且这一轮**必须走 attach 通道**（否则 `_sides` 不被读 ⇒ 又没有分辨力）
#
# ## 判据（**预先写死**）
# | 臂 | 必须 |
# |---|---|
# | S2 正对照 | **PASS** |
# | **负 4（翻转奇偶）** | **★ FAIL** |
# ## ★ 分辨力先验：窗口内**必须**出现 `模式 attach`
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_nc6
LOG=_w2_r581_nc6.log
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
  local tag="$1" extra="$2" st="$3"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $CFG --steps "$st" $extra \
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_nc6_${tag}.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_nc6_${tag}.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say '=== ① S1：只写 step 0 那一帧 ==='
run nc6_s1 "--ckpt-every 1 --ckpt-keep 2" 0
say "=== ② S3：连续跑 $STEPS 步（真值）==="
run nc6_s3 "" "$STEPS"

say '=== ③ ★ 分辨力先验：窗口内**必须**出现 attach 模式的形核 ==='
ATT=$(awk '/模式 \*\*attach\*\*|模式 attach/' "_w2_r581_nc6_nc6_s3.log" 2>/dev/null | wc -l)
say "  含「模式 attach」的行 = **$ATT**（必须 ≥1，否则 \`_sides\` 不被读 ⇒ 又无分辨力）"
grep -oE '模式 \*?\*?attach\*?\*?' "_w2_r581_nc6_nc6_s3.log" 2>/dev/null | head -3 | sed 's/^/    /'
if [ "$ATT" -lt 1 ]; then
  say '  ❌ **这一轮没走 attach 通道 ⇒ 负 4 无分辨力** ⇒ 停（不许硬测）'
  exit 2
fi
say '  ✅ 走的是 attach 通道 ⇒ 负 4 有分辨力'

say "=== ④ S2：正对照（step 0 → $STEPS）==="
run nc6_s2 "--resume $ROOT/dry_nc6_s1/ckpt" "$STEPS"
grep -E '自动选|检查点 step=|驱动层已回填' "_w2_r581_nc6_nc6_s2.log" 2>/dev/null | sed 's/^/    /'

say '=== ⑤ 负 4（**翻转奇偶**）==='
REAL=$($PY - <<'PYEOF'
import os, numpy as np
d = '_exp/_bk_nc6/dry_nc6_s1/ckpt'
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
say "  源帧 = $REAL"
BAD="$ROOT/dry_neg_dbg_ok_odd.npz"
$PY _r581_ckpt_negctl.py "$REAL" "$BAD" dbg_ok_odd 6 2>&1 | sed 's/^/  /'
run nc6_n4 "--resume $BAD" "$STEPS"

say '════ 汇总 ════'
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, sys
sys.path.insert(0, '.')
from _r581_ckpt_cmp import cell_bits, load
ROOT = sys.argv[1]
ref = load(os.path.join(ROOT, 'dry_nc6_s3', 'series.csv'))
mref = {r['step']: r for r in ref}
cols = [c for c in ref[0] if c != 'wall_s']
print()
print('  %-9s %-32s %-12s %-11s %s' % ('臂', '说明', '判据', '实测差异', '判定'))
print('  ' + '-' * 90)
for tag, name, want in (('nc6_s2', '正对照（不破坏）', 'PASS'),
                        ('nc6_n4', '★ 负4 `dbg[ok]` **翻转奇偶**', 'FAIL')):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        print('  %-9s %-32s %-12s %s' % (tag, name, want, '（缺失）'))
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
    print('  %-9s %-32s %-12s %-11s %s %s' %
          (tag, name, want, ('%d 处' % nd) if nd else '**0**',
           '✅' if got == want else '❌',
           dict(sorted(bad.items(), key=lambda x: -x[1])[:4]) if bad else ''))
print()
print('  ★ 若 FAIL ⇒ **证明 `dbg[ok]` 的奇偶真的驱动动力学**，且上一轮的 PASS')
print('     是**判据缺陷**（归零没改奇偶），不是"它不重要"。')
PYEOF
say '=== NC6 DONE ==='
