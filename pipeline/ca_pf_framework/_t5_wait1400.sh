#!/bin/bash
# _t5_wait1400.sh --- 第 23 条机制：等 `snap_01400`，验**新预测**（紧凑场 < 6）
#
# ## 判据（**预先写死**，§185.3 附注）
# 上一张 band 快照（step 1200）里：带延伸 **18**、紧凑 **6**。
# **新预测：step 1400 的 band 快照里，紧凑场应 **< 6**（该形貌转变接近完成）。**
#   * 紧凑 < 6 ⇒ **预测成立**（转变继续传播）
#   * 紧凑 = 6 或 > 6 ⇒ **预测不成立**（转变停止或回退）⇒ 须记账
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
D=_exp/_bk_t5/dry_t5H3
S=$D/series.csv
DEADLINE=$(( $(date +%s) + 7200 ))      # 最多等 2 小时
echo "[$(date '+%F %T')] 开始等：t5H3 末步 >= 1400（或 snap_01400 出现）"
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  ST=$(tail -1 "$S" 2>/dev/null | cut -d, -f1); [ -z "$ST" ] && ST=0
  if [ -f "$D/snap_01400.npz" ] || [ "$ST" -ge 1400 ] 2>/dev/null; then break; fi
  sleep 60
done
echo "[$(date '+%F %T')] t5H3 末步 = $(tail -1 "$S" 2>/dev/null | cut -d, -f1)"
echo
if [ -f "$D/snap_01400.npz" ]; then
  echo '════ ★ snap_01400 到 ⇒ 跑充填率时间序列 ════'
  taskset -c 16-19 $PY _t5_fillts.py 2>&1 | tail -12
  echo
  echo '════ 判据（**预先写死**）════'
  taskset -c 16-19 $PY - <<'PYEOF'
import numpy as np
P = '_exp/_bk_t5/dry_t5H3/snap_01400.npz'
try:
    with np.load(P, allow_pickle=False) as z:
        if 'band_fld' not in z.files:
            print('  ⚠ snap_01400 无 band（band 每 200 步 ⇒ 1400 不是 200 的倍数？）')
            raise SystemExit
        fld = np.asarray(z['band_fld']).ravel()
        bidx = np.asarray(z['band_idx']).ravel()
        reg = np.asarray(z['region'])
    coords = np.unravel_index(bidx.astype(np.int64), reg.shape)
    # ⚠ 用**完整 region**（§160 定的更正确口径）：这里为速度仍用 band∩region，但注明
    reg_at = reg[coords]
    tight = ext = 0
    for f in sorted(set(int(x) for x in np.unique(fld).tolist())):
        if f == 0: continue
        sel = (fld == f) & (reg_at > 0)
        if not sel.any(): continue
        cc = np.stack([c[sel] for c in coords], axis=1)
        lo, hi = cc.min(0), cc.max(0)
        fill = float(sel.sum()) / max(int(np.prod(hi - lo + 1)), 1)
        if fill >= 0.10: tight += 1
        else: ext += 1
    print('  step 1400：紧凑 = **%d**，带延伸 = **%d**' % (tight, ext))
    print('  判据：紧凑 < 6 ⇒ **预测成立**；>= 6 ⇒ **不成立**（须记账）')
    print('  ⇒ **%s**' % ('✅ 预测成立（转变继续传播）' if tight < 6 else
                          '❌ 预测**不成立**（转变停止或回退）—— 须记账'))
PYEOF
else
  echo '  ⇒ snap_01400 仍未到 ⇒ 不重复查（另起作业或下次再说）'
fi
