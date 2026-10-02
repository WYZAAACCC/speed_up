#!/bin/bash
# _r581_vtunit.sh --- ★★ 核实一件容易埋雷的事：
#   **同一名字 `Vt` 在两条通道里是不是同一个单位？**
#     · stdout 横幅：`[ 200] Vt=0.6194 µm³ | ...`（`_r581_p2.py` 的 RE_STEP 抓的就是它）
#     · series.csv 列：`Vt`（R35 实测是 **SI m³**）
cd "$(dirname "$0")" || exit 1
echo '=== ① stdout 横幅里的 Vt（step 200 那一行）==='
for t in p2_b5 p2_b3; do
  echo "  ── $t ──"
  grep -aE '^  \[\s*200\]' "_w2_r581_p2_${t}.log" 2>/dev/null | head -1 | cut -c1-120 | sed 's/^/    /'
done
echo
echo '=== ② series.csv 里 step=200 的 Vt 原始值 ==='
for t in p2_b5 p2_b3; do
  v=$(awk -F, 'NR==1{for(i=1;i<=NF;i++) if($i=="Vt") c=i; next} $1==200 {print $c; exit}' \
        "_exp/_bk_p2/dry_${t}/series.csv" 2>/dev/null)
  echo "  $t : Vt = $v  （×1e18 = $(awk -v x="$v" 'BEGIN{printf "%.6f", x*1e18}') µm³）"
done
echo
echo '=== ③ 从快照独立数胞（自洽检查）==='
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import os
import numpy as np
for t in ('p2_b5', 'p2_b3'):
    p = '_exp/_bk_p2/dry_%s/snap_00200.npz' % t
    if not os.path.exists(p):
        print('  %s : 无快照' % t); continue
    z = np.load(p)
    reg = z['region']; L = float(z['L']); dx = L / reg.shape[0]
    n = int((reg > 0).sum())
    print('  %s : %d 胞 × Δx³ = **%.6f µm³**' % (t, n, n * dx ** 3 * 1e18))
PYEOF
echo
echo '=== 判读 ==='
echo '  若 ① 的数字（µm³）≈ ② × 1e18 ≈ ③，则：'
echo '    **stdout 横幅用 µm³，series.csv 用 SI m³ —— 同一个名字、两个单位。**'
echo '  ⇒ 这是个**必须写进纪律的雷**：跨通道取 `Vt` 一定要对单位。'
