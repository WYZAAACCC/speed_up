#!/usr/bin/env bash
# _round36.sh --- 两件事：
#   ① **记账**：`f_imp` 的旧值 0.038 是用 `t=100 nm` 算的；种子改到 `t=200 nm` 后
#      `f_imp = (π/4)(t/d) = (π/4)(200/1600) = 0.098` ⇒ "刚碰撞后"在 **f≈0.10**，
#      比预算远 3 倍（约 1300 步 / ~16 h 每档）⇒ **本预算内只能采"碰撞前"**。
#   ② 因此把 T13b 的 `f_target` 从 0.06 降到 **0.035**（撞出 break 线 0.040），
#      使**首个采样点能在 ~2 h 内落盘**（否则要等 f≥0.069、约 8.6 h 才打印）。
#   ⚠ 记账：T13b 的 break 条件是 `f >= f_target*1.15`，所以 `f_target=0.035` ⇒ 停在 f≈0.040，
#      这是**碰撞前**的态 —— 交付时必须标 "pre-impingement"。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
print('f_imp 复核：')
for t_nm, d_um, n in ((100, 1.6, 64), (200, 1.6, 64), (200, 2.068, 100)):
    import math
    print('  t=%3d nm, d=%.3f µm ⇒ f_imp=(π/4)(t/d) = %.4f' %
          (t_nm, d_um, math.pi / 4 * (t_nm * 1e-9) / (d_um * 1e-6)))
EOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T13b_verify_nv*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T13b_verify_nv.py --dx-nm 50 --ns 64,128,256 \
        --f-target 0.035 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-48
free -g | head -2
