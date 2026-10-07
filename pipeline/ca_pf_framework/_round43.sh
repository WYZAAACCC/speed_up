#!/usr/bin/env bash
# _round43.sh --- **把采样目标从"刚碰撞后"改为"统计量够用"**（本会话最大的一次省时决定）。
#
# 理由（全部是本会话实测出来的）：
#   ① "刚碰撞后" = `f_imp = (π/4)(t/d) = 0.098`（t=200 nm, d=1.6 µm）⇒ ~1300 步 ⇒ **不可达**；
#   ② 于是采样点的**真正约束**变成"转变体积够不够统计稳定"，而不是"是否碰撞"；
#   ③ 实测轨迹：从种子到 `f≈0.023` 只需 **~45–50 步**（早期增量大：0.0017→0.0164 用 20 步），
#      而到 `f=0.040` 要 **~460 步** ⇒ **同一档，前者 ~25 min、后者 ~5 h**。
#   ⇒ 把 `f_target` 从 0.035 降到 **0.02**（break 线 0.023）⇒ **三个作业全部提前 10× 以上**。
#
# ⚠ 记账（必须随结果交付）：采样点是 **pre-impingement 的早期态**
#   （`f/f_imp ≈ 0.24`）。`Sv`/`r_c^var`/`M6p` 在这个 `f` 上稳不稳，**由这次的读数自己检验**：
#   若三档之间 `Sv` 的散布明显大于以往（>10%），就说明 f 还太小，再拉长。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
import math
print('f_imp 复核（(π/4)(t/d)）：')
for lab, t_nm, d_um in (('T13b n=64/128/256', 200, 1.6), ('T16 n0=100', 200, 2.068),
                        ('T24 n0=64', 200, 1.6)):
    print('  %-20s f_imp = %.4f' % (lab, math.pi / 4 * t_nm * 1e-9 / (d_um * 1e-6)))
EOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T13b_verify_nv*|*T16_verify_rve*|*T24_verify_grouping*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3

setsid nohup "$PY" -u T13b_verify_nv.py --dx-nm 50 --ns 64,128,256 \
        --f-target 0.02 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b pid=$!"
setsid nohup "$PY" -u T16_verify_rve.py --L-um 9.6 --dx-nm 50 --n0 100 \
        --f-target 0.02 --adv proj2 > _t16prod.log 2>&1 < /dev/null &
echo "T16  pid=$!"
setsid nohup "$PY" -u T24_verify_grouping.py --mode rve --L-um 6.4 --dx-nm 50 \
        --n0 64 --f-target 0.02 --adv proj2 > _t24rve.log 2>&1 < /dev/null &
echo "T24  pid=$!"
sleep 25
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-50
free -g | head -2
