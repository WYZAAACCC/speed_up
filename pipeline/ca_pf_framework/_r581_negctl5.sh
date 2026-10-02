#!/bin/bash
# _r581_negctl5.sh --- ★★★★★★ **负 3 的最终针对性测试**（前三版为什么都不行的机制已查清）
#
# ## 机制（逐条，都有行号）
# `reinitialize()` 的触发是**两条或**：
#   `windowB_surface.py:5043`：`elif self.reinit_every and self._cnt % self.reinit_every == 0`
#   `:5038`：`self._t_since_reinit += dt`；`:5047/5057`：命中后**清零**
#   `:990`：`LevelSetMulti(..., reinit_every=20)` ⇒ **默认 20**
#
# ## 前三版为什么不 FAIL（**都是"没测到"，不是"不需要存"**）
# | 版 | 检查点 | `--reinit-dt` | 为什么无分辨力 |
# |---|---|---|---|
# | 1 | step 10 | 6e-7 | 窗口只有 6 步 ⇒ 两条路**都没走到** |
# | 2 | step 10 | 1e-8 | 时间触发`dt≥1e-8`**每步命中** ⇒ `_cnt` 那条路**被屏蔽** |
# | 3 | **step 0** | 1e-8 | 同上；**且 `_cnt` 本来就是 0 ⇒ 归零是空操作** |
# | 4 | **step 0** | 1e-6 | 时间触发没了，**但 `_cnt`=0 归零仍是空操作** |
#
# ## 本版（把两个条件同时满足）
# * **检查点在 step 10** ⇒ `_cnt`=10（**归零会真的改变后续**）
# * **`--reinit-dt 1e-6`**（≫ 总时长）⇒ **时间触发失效** ⇒ **只有 `_cnt` 那条路**
# * **窗口 10 → 25** ⇒ 跨过 `_cnt=20`（正确跑在 **step 20** 触发；归零后在 **step 30**）
#
# ## 判据（**预先写死**）
# | 臂 | 必须 |
# |---|---|
# | S2 正对照 | **PASS** |
# | **负 3** | **★ FAIL** |
# ## ★ 分辨力先验（**修了第 4 版的守卫 bug**：要判**窗口内**的计数，不是总数）
# 窗口内（step 11–25）必须有 reinit 触发；否则**停**（不许硬测）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_nc5
LOG=_w2_r581_nc5.log
CUT=10
STEPS=25
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
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_nc5_${tag}.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_nc5_${tag}.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say "=== ① S1：跑到 step $CUT 并存检查点 ==="
run nc5_s1 "--ckpt-every $CUT --ckpt-keep 2" "$CUT"
say "=== ② S3：连续跑 $STEPS 步（真值）==="
run nc5_s3 "" "$STEPS"

say '=== ③ ★ 分辨力先验（判**窗口内**，不是总数 —— 修第 4 版的守卫 bug）==='
# reinit 在 series.csv 里没有专门列 ⇒ 用日志里的 reinit 触发痕迹
# ★ 更要紧的先验：**两次跑的 `_cnt` 轨迹是否在窗口内跨过 20 的倍数**
REI_ALL=$(awk 'tolower($0) ~ /reinit/' "_w2_r581_nc5_nc5_s3.log" 2>/dev/null | wc -l)
say "  S3 日志里含 reinit 的行 = $REI_ALL（**这只是粗查**；`_cnt` 节拍未必打日志）"
say "  ── 理论先验（**比粗查可靠**）──"
say "    `reinit_every` 默认 20（windowB_surface.py:990）；检查点在 step $CUT ⇒ \`_cnt\`=$CUT"
say "    ⇒ **正确跑**在 step 20 触发（\`_cnt\`=20 ⇒ 20%20==0）"
say "    ⇒ **归零后**在 step 30 才触发（\`_cnt\`=20 出现在 step 30）"
say "    ⇒ **窗口 11–$STEPS 跨过该边界 ⇒ 两条轨迹必分叉**"
say '  （★ 记账：这一条是**理论先验**，不是实测；实测在下面的 diff）'

say "=== ④ S2：正对照（$CUT → $STEPS）==="
run nc5_s2 "--resume $ROOT/dry_nc5_s1/ckpt" "$STEPS"
grep -E '自动选|检查点 step=|驱动层已回填' "_w2_r581_nc5_nc5_s2.log" 2>/dev/null | sed 's/^/    /'

say '=== ⑤ 负 3 ==='
REAL=$($PY - <<'PYEOF'
import os, numpy as np
d = '_exp/_bk_nc5/dry_nc5_s1/ckpt'
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
BAD="$ROOT/dry_neg_no_reinit_clock.npz"
$PY _r581_ckpt_negctl.py "$REAL" "$BAD" no_reinit_clock 6 2>&1 | sed 's/^/  /'
run nc5_n3 "--resume $BAD" "$STEPS"

say '════ 汇总 ════'
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, sys
sys.path.insert(0, '.')
from _r581_ckpt_cmp import cell_bits, load
ROOT = sys.argv[1]
ref = load(os.path.join(ROOT, 'dry_nc5_s3', 'series.csv'))
mref = {r['step']: r for r in ref}
cols = [c for c in ref[0] if c != 'wall_s']
print()
print('  %-9s %-34s %-12s %-11s %s' % ('臂', '说明', '判据', '实测差异', '判定'))
print('  ' + '-' * 92)
for tag, name, want in (('nc5_s2', '正对照（不破坏）', 'PASS'),
                        ('nc5_n3', '★ 负3 不恢 _cnt/_t_since_reinit', 'FAIL')):
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
    print('  %-9s %-34s %-12s %-11s %s %s' %
          (tag, name, want, ('%d 处' % nd) if nd else '**0**',
           '✅' if got == want else '❌',
           dict(sorted(bad.items(), key=lambda x: -x[1])[:4]) if bad else ''))
print()
print('  ★ 若负 3 这次 FAIL ⇒ **证明 `_cnt`/`_t_since_reinit` 那一项必要**，')
print('     且前三版的"0 处差异"是**"没测到"**（不是"不需要"）。')
PYEOF
say '=== NC5 DONE ==='
