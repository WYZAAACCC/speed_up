#!/usr/bin/env bash
# _relaunch_df35.sh --- 用**物理修正后的 Δf = 3.5e8**（D7 文献 ΔG@298 K）重排生产统计。
#   依据：`_probe_growth.py` 门控实测 —— Δf=2e8 有弹性时 dV/V0 只有 0.170（无弹性 1.587）
#   ⇒ f=0.10 不可达（T16/T24 跑到 2 h 无采样点就是这个原因）。
#   同时把 f_target 降到 **0.06**（碰撞分数 f_imp≈0.038 的 1.6 倍，"刚碰撞后"）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T16_verify_rve*|*T24_verify_grouping*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
$PY - <<'EOF'
import ast
for f in ('T16_verify_rve.py', 'T13b_verify_nv.py', 'T24_verify_grouping.py'):
    ast.parse(open(f).read())
print('SYNTAX OK')
EOF

setsid nohup "$PY" -u T16_verify_rve.py --L-um 9.6 --dx-nm 50 --n0 100 \
        --f-target 0.06 --adv proj2 > _t16prod.log 2>&1 < /dev/null &
echo "T16   pid=$!"
setsid nohup "$PY" -u T13b_verify_nv.py --L-um 9.6 --dx-nm 75 --ns 64,128,256 \
        --f-target 0.06 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b  pid=$!"
setsid nohup "$PY" -u T24_verify_grouping.py --mode rve --L-um 9.6 --dx-nm 75 \
        --n0 64 --f-target 0.06 --adv proj2 > _t24rve.log 2>&1 < /dev/null &
echo "T24   pid=$!"
sleep 25
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-70
free -g | head -2
