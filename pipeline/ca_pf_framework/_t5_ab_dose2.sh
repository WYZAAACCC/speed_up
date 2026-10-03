#!/bin/bash
# _t5_ab_dose2.sh --- ★★★★★ 剂量-响应（**只补 5 与 7 两个点**；3.75 点复用已跑的 t5AB_B）
#
# ## 为什么只起 2 臂
# 已跑的 A/B 里 **`t5AB_B` 就是 `eng-elong=3.75` 的剂量点**（同 N=80、同 nvar/m/B、同 facet=0）
# ⇒ **剂量-响应只差 5 与 7** ⇒ **只需 2 臂（~5 GB）**，而不是原计划的 4 臂（~10 GB，会到 21 GB）。
# **⇒ 这是"复用已有数据"省下来的内存**（也避免了 AGENTS.md §3.12 的卡死风险）。
#
# ## 设计（**预先写死**）
# | 剂量点 | 来源 |
# |---|---|
# | **0**    | **`t5AB_A`**（已跑，对照）|
# | **3.75** | **`t5AB_B`**（已跑）|
# | **5**    | **`t5AD_500`**（本脚本起）|
# | **7**    | **`t5AD_700`**（本脚本起）|
# **参数与 `t5AB_*` 逐项一致**（N=80 / nvar 3 / m 24 / B 3 / 1400 步 / cores 0-3 / overlap 62.5 / facet-proj 0）
# ⇒ **唯一变量 = `--eng-elong`** ✓
#
# ## 判据（**预先写死**）
# 1. **单调性**：长宽比应随 `eng-elong` 单调上升（0 < 3.75 ≤ 5 ≤ 7）；
# 2. **饱和信号**：若 **7 与 5 的差 < 5%** ⇒ **核的拉长已饱和**
#    （**与 §212 一致**：生长阶段不拉长 ⇒ 最终比例 ≈ 核的比例）；
# 3. **⚠ 副作用闸**：任一新臂**报错**（如 `elong*R > margin` 越界）或**场数骤减** ⇒ 该档不可用；
# 4. **⚠ 时序闸（第 28 条）**：判据只认**同一末步**上的读数，且至少要 **3 个不同步点**的趋势。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ab_dose.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════════ 剂量-响应（补 5 与 7；0 与 3.75 复用 t5AB_A / t5AB_B）════════'
say '  参数与 t5AB_* 逐项一致 ⇒ 唯一变量 = --eng-elong'
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

for spec in "t5AD_500 5.00" "t5AD_700 7.00"; do
  set -- $spec
  TAG=$1; EL=$2
  $PY _t5_short.py --tag "$TAG" --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
      --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
      --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 --eng-elong "$EL" \
      > _w2_t5_ad_${TAG}.log 2>&1 &
  say "  起 $TAG：eng-elong=$EL  pid=$!"
done
sleep 60
free -m | sed -n 2p | awk '{printf "  起后 60 s 内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
say '  ── 等两臂结束（本脚本一直等）──'
wait
say '════ 两臂结束 ⇒ 剂量-响应汇总（含复用的 0 与 3.75）════'
$PY - <<'PYEOF' >> "$LOG" 2>&1
import glob, numpy as np
DX = 62.5
# (标签, tag 目录, eng-elong 值)
ARMS = [('0（对照）', 't5AB_A', 0.0), ('3.75', 't5AB_B', 3.75),
        ('5', 't5AD_500', 5.0), ('7', 't5AD_700', 7.0)]
print('  %-12s %-9s %-7s %-22s %s' % ('剂量(eng-elong)', '臂', '场数', '长宽比 中位 [范围]', '长厚比 中位 [范围]'))
print('  ' + '-' * 92)
rows = []
for lab, tag, el in ARMS:
    sn = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag))
    if not sn:
        print('  %-12s %-9s （无快照）' % (lab, tag)); continue
    with np.load(sn[-1], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    ar, lt = [], []
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8: continue
        c = idx - idx.mean(0); w, v = np.linalg.eigh(c.T @ c); o = np.argsort(w)[::-1]
        p = [float((c @ v[:, j]).max() - (c @ v[:, j]).min() + 1) * DX / 1000.0 for j in o[:2]]
        if nh is not None:
            ax = nh / (np.linalg.norm(nh) + 1e-300)
            t = float((c @ ax).max() - (c @ ax).min() + 1) * DX / 1000.0
        else:
            t = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        ar.append(p[0] / max(p[1], 1e-9)); lt.append(p[0] / max(t, 1e-9))
    st = int(sn[-1].split('snap_')[1].replace('.npz', ''))
    if ar:
        print('  %-12s %-9s %-7d %6.2f [%.2f, %.2f]%8s %6.2f [%.2f, %.2f]   (step %d)'
              % (lab, tag, len(ar), np.median(ar), min(ar), max(ar), '',
                 np.median(lt), min(lt), max(lt), st))
        rows.append((el, float(np.median(ar)), float(np.median(lt))))
print()
if len(rows) >= 2:
    rows.sort()
    print('  ── 单调性检查 ──')
    for i in range(1, len(rows)):
        d = rows[i][1] - rows[i-1][1]
        print('    eng-elong %-5s → %-5s ：长宽比 %+.2f  ⇒ %s'
              % (rows[i-1][0], rows[i][0], d, '升 ✅' if d > 0.05 else '**持平/降 ⚠（饱和信号）**'))
print()
print('  判据（预先写死）：1) 单调上升；2) 7 与 5 差 <5% ⇒ 核的拉长已饱和（与 §212 一致）；')
print('                    3) 任一新臂报错或场数骤减 ⇒ 该档不可用；4) 只认同一末步 + ≥3 个步点趋势。')
PYEOF
say '=== AB_DOSE2 DONE ==='
