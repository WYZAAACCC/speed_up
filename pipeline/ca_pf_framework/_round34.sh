#!/usr/bin/env bash
# _round34.sh --- T21 夹逼：**改回 2.0e-3**（Round 31/32 我把它降到 1.3e-3 是**方向错了** ——
#   种子分数实测是 **1.66e-3**，参考点必须在它**之上**才可能有 `f_lo`）。
#   ⇒ 正解 = **种子态采样（Round 32 加的，保留）+ f_ar_ref=2.0e-3**。
#   夹逼链：f_seed=1.66e-3 (step 0) < 2.0e-3 < f(5)=2.05e-3 ⇒ 必然夹住 ✓
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
import ast
p = 'T21_beta_calib.py'
s = open(p).read()
s = s.replace('f_ar_ref=1.3e-3):', 'f_ar_ref=2.0e-3):')
open(p, 'w').write(s)
ast.parse(s)
print('SYNTAX OK, f_ar_ref -> 2.0e-3（种子分数 1.66e-3 之上）')
EOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T21_beta_calib*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25 \
        --betas 0,1.5,3.5,6.5 --f-target 0.05 > _t21g.log 2>&1 < /dev/null &
echo "T21g pid=$!"
sleep 40
grep -E '轨迹 β=0.0' _t21g.log | head -3
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-48
