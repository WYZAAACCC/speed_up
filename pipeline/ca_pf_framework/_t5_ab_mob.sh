#!/bin/bash
# _t5_ab_mob.sh --- ★★★★★ 验"迁移率各向异性公式是否真起作用" + 与 `--eng-elong` 叠加（2×2）
#
# ## 目标（用户原话）
# > **「起这个验证，验证一下当前的物理公式是否真正起作用，
# >   如果起作用，就将其和已经证明有效的 --eng-elong 叠加在一起试一下」**
#
# ## 设计（**2×2，复用两条已跑的臂 ⇒ 只需新起 2 条**）
# |                    | `mob-iform=exp2`（默认）| **`mob-iform=ellipse`** |
# |--------------------|------------------------|------------------------|
# | **`eng-elong=0`**  | **`t5AB_A`**（已跑）    | **`t5AM_ell`**（新起）← **验公式** |
# | **`eng-elong=7`**  | **`t5AD_700`**（已跑）  | **`t5AM_combo`**（新起）← **叠加** |
# **新臂参数与 `t5AB_*`/`t5AD_*` 逐项一致**（N=80/nvar3/m24/B3/1400步/cores 0-3/overlap 62.5/facet-proj 0）
# ⇒ **唯一变量 = 这两个开关** ✓
#
# ## 为什么 `mob-ratio` 也传（=9）
# 代码注释逐字：「极集本身凸 ⇒ 凸化恒等 ⇒ `h(a)/h(w)` **恰等于 --mob-ratio**」⇒
# **不传它就用默认 9.0 ⇒ 一样**；但**显式传**可以**排除"默认值被别处改过"的可能**（第 30 条的同族谨慎）。
#
# ## 判据（**预先写死**）
# 1. **【公式是否起作用】** `t5AM_ell`（ellipse, elong=0）的长宽比 **应显著 > `t5AB_A`（1.85）**；
#    * **仓库自己记着**：「解析各向异性 9.90、**引擎实际 1.24**」（那是 `exp2` 形式）
#      ⇒ **若 `ellipse` 也上不去（如仍 ~2）⇒ **公式未真正起作用****，须记账并**不进入叠加**；
# 2. **【叠加是否更好】** `t5AM_combo`（ellipse + elong7）**应 ≥ max(`t5AD_700`=6.55, `t5AM_ell`)**；
#    * 若 **≈ `t5AD_700`** ⇒ **两机制**不叠加**（可能饱和或互相遮挡）⇒ 记账；
# 3. **⚠ 时序闸（第 28 条）**：只认**同一末步**、且要点数 ≥3 的趋势；
# 4. **⚠ 副作用闸**：同时刻**场数**与对照一致（§228 已验 `eng-elong` 无副作用；本开关**未验**）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ab_mob.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════════ 2×2 验迁移率各向异性（ellipse）× eng-elong（7）════════'
say '  复用：t5AB_A(exp2,elong0) · t5AD_700(exp2,elong7)；新起：t5AM_ell · t5AM_combo'
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

# ① t5AM_ell：只开 ellipse（elong 不传 ⇒ 0）—— **验公式**
$PY _t5_short.py --tag t5AM_ell --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 \
    --mob-iform ellipse --mob-ratio 9.0 \
    > _w2_t5_am_t5AM_ell.log 2>&1 &
say "  起 t5AM_ell：mob-iform=ellipse ratio=9  pid=$!"

# ② t5AM_combo：ellipse + eng-elong 7 —— **验叠加**
$PY _t5_short.py --tag t5AM_combo --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 \
    --eng-elong 7.00 --mob-iform ellipse --mob-ratio 9.0 \
    > _w2_t5_am_t5AM_combo.log 2>&1 &
say "  起 t5AM_combo：eng-elong=7 mob-iform=ellipse  pid=$!"

sleep 90
free -m | sed -n 2p | awk '{printf "  起后 90 s 内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
echo '  ── 两臂的构造横幅关键行（先验：确认参数真的进去了）──' >> "$LOG"
for t in t5AM_ell t5AM_combo; do
  echo "  ── $t ──" >> "$LOG"
  grep -nE "mob.iform|mob.ratio|ellipse|迁移率|eng.elong" _w2_t5_am_$t.log 2>/dev/null \
    | head -4 | cut -c1-150 >> "$LOG"
done
say '  ── 等两臂结束（本脚本一直等）──'
wait
say '════ 两臂结束 ⇒ 2×2 汇总（用已验证量具）════'
$PY - <<'PYEOF' >> "$LOG" 2>&1
import glob, numpy as np
DX = 62.5
CELLS = [('eng-elong=0, exp2  ', 't5AB_A'),
         ('eng-elong=0, ellipse', 't5AM_ell'),
         ('eng-elong=7, exp2  ', 't5AD_700'),
         ('eng-elong=7, ellipse', 't5AM_combo')]
print('  %-24s %-7s %-24s %s' % ('配置', '场数', '长宽比 中位 [范围]', '长厚比 中位 [范围]'))
print('  ' + '-' * 92)
for lab, tag in CELLS:
    sn = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag))
    if not sn:
        print('  %-24s （无快照）' % lab); continue
    with np.load(sn[-1], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    ar, lt, thin = [], [], 0
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
        if t < 0.25: thin += 1
    st = int(sn[-1].split('snap_')[1].replace('.npz', ''))
    if ar:
        print('  %-24s %-7d %6.2f [%.2f, %.2f]%8s %6.2f [%.2f, %.2f]  (step %d)%s'
              % (lab, len(ar), np.median(ar), min(ar), max(ar), '',
                 np.median(lt), min(lt), max(lt), st,
                 '  ⚠%d场厚<4胞' % thin if thin else ''))
print()
print('  判据（预先写死）：1) ellipse(elong0) 应显著 > 1.85 ⇒ 公式起作用；否则记账、不叠加；')
print('                    2) combo 应 >= max(6.55, ellipse)；若 ≈6.55 ⇒ 两机制不叠加；')
print('                    3) 只认同一末步 + >=3 个步点的趋势；4) 副作用闸：同时刻场数应一致。')
PYEOF
say '=== AB_MOB DONE ==='
