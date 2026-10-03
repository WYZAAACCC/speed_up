#!/bin/bash
# _t5_ab_dose.sh --- ★★★★★ `--eng-elong` 的**剂量-响应** A/B（3.75 / 5 / 7 / 对照）
#
# ## 为什么（§217 之后必然的下一步）
# §217 实测 `--eng-elong 3.75` 有效（长宽比 1.85 → **3.55**，~1.92×）。
# 但 **3.75 只是"驱动层的 L/W = 2400/640"这一个值** ⇒
# **⇒ 必须回答两件事**：
#   ① **更高会更好吗**（长宽比是否随之升高）？
#   ② **有没有上限/副作用**（是否会更早撞盒、或改变 `plate_L` 相关的几何检查）？
#
# ## 设计（**预先写死**）
# | 臂 | tag        | --eng-elong |
# |----|------------|-------------|
# | a  | t5AD_375   | **3.75**（复现 §217 的 B）|
# | b  | t5AD_500   | **5.00** |
# | c  | t5AD_700   | **7.00** |
# | d  | t5AD_0     | **0**（对照）|
# **N=80 / 400 步**（先看**早期趋势**，省时省内存；长跑另议）
#
# ## 判据（**预先写死**）
# 1. **单调性**：长宽比 应随 `eng-elong` 单调上升（375 < 500 < 700）；
# 2. **上限信号**：若 **700 与 500 差不多** ⇒ 说明**核的拉长已到顶**
#    （因为**生长阶段不拉长** —— §212 ⇒ 最终比例 ≈ 核的比例）；
# 3. **⚠ 副作用闸**：若某臂**报错**（`elong*R > margin` 之类的越界检查）或**场数骤减**
#    ⇒ **该档不可用**，须记账；
# 4. **⚠ 对照闸**：`t5AD_0` 的长宽比应 ≈ **1.8–1.9**（= §217 的 A）⇒ 否则本批不可比。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ab_dose.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════════ 剂量-响应 A/B：--eng-elong 0 / 3.75 / 5 / 7 ════════'
say '  N=80（5 µm）· 400 步 · 并行 · 判据见脚本头（预先写死）'
free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

run() {   # $1=tag  $2=elong
  local TAG=$1 EL=$2 ARGS=""
  [ "$EL" != "0" ] && ARGS="--eng-elong $EL"
  $PY _t5_short.py --tag "$TAG" --N 80 --nvar 3 --m 24 --B 3 --steps 400 \
      --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
      --ckpt-every 200 --ckpt-keep 1 --overlap-nm 62.5 $ARGS \
      > _w2_t5_ad_${TAG}.log 2>&1 &
  say "  起 $TAG：eng-elong=$EL  pid=$!"
}

run t5AD_375 3.75
run t5AD_500 5.00
run t5AD_700 7.00
run t5AD_0   0

say '  ── 等四臂结束（本脚本一直等）──'
wait
say '════ 四臂结束 ⇒ 自动测长宽比/长厚比（用已验证量具）════'
$PY - <<'PYEOF' >> "$LOG" 2>&1
import glob, numpy as np
DX = 62.5
print('  %-10s %-8s %-7s %-26s %s' % ('臂', 'eng-elong', '场数', '长宽比 中位 [范围]', '长厚比 中位 [范围]'))
print('  ' + '-' * 88)
for tag, el in (('t5AD_375', 3.75), ('t5AD_500', 5.0), ('t5AD_700', 7.0), ('t5AD_0', 0.0)):
    sn = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag))
    if not sn:
        print('  %-10s %-8s （无快照）' % (tag, el)); continue
    with np.load(sn[-1], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    ar, lt = [], []
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8: continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        p = [float((c @ v[:, j]).max() - (c @ v[:, j]).min() + 1) * DX / 1000.0 for j in o[:2]]
        if nh is not None:
            ax = nh / (np.linalg.norm(nh) + 1e-300)
            t = float((c @ ax).max() - (c @ ax).min() + 1) * DX / 1000.0
        else:
            t = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        ar.append(p[0] / max(p[1], 1e-9)); lt.append(p[0] / max(t, 1e-9))
    if ar:
        print('  %-10s %-8s %-7d %6.2f [%.2f, %.2f]%14s %6.2f [%.2f, %.2f]'
              % (tag, el, len(ar), np.median(ar), min(ar), max(ar), '',
                 np.median(lt), min(lt), max(lt)))
print()
print('  ── 判据（预先写死）──')
print('  1) 单调性：长宽比应随 eng-elong 单调上升')
print('  2) 上限信号：700 与 500 差不多 ⇒ 核的拉长已到顶（因生长阶段不拉长）')
print('  3) 副作用闸：若某臂报错或场数骤减 ⇒ 该档不可用')
print('  4) 对照闸：t5AD_0 应 ≈ 1.8–1.9（= §217 的 A）')
PYEOF
say '=== AB_DOSE DONE ==='
