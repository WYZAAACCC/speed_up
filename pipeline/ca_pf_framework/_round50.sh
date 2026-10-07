#!/usr/bin/env bash
# _round50.sh --- T13b 三处修 + 重跑（针对 Round 49 的两个报警）
#   ① **解耦采样门槛与目标**：门槛原为 `max(0.5·f_target, 0.02)` —— 当 `f_target ≤ 0.04`
#      时门槛恒为 0.02，而第一个样本落在 0.0202 ⇒ **必然不夹逼**。改成 `0.5·f_target`（去掉 0.02 地板）。
#   ② **采样点下移到绕盒起始之前**：Round 49 实测**逐变体绕盒在 `f≈0.021–0.023` 就发生**
#      （`f=0.0202` 时还 ok）。物理原因【推理】是**各向异性展平**：`mob_beta=3.5` 让厚度每秒
#      只长 0.03×，而面内全速 ⇒ 面内半径涨得比体积分数快得多 ⇒ **`f` 还很低时板条就已相互接触**。
#      ⇒ 取 `f_target = 0.016`（break 线 0.0184）⇒ **采在绕盒之前**。
#   ③ **打印绕盒细节**（哪个变体、哪个轴）便于判定真贯通 vs 假阳性。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'PYEOF'
import ast
p = 'T13b_verify_nv.py'
s = open(p).read()
# ① 解耦门槛
old1 = "        if f_now < max(0.5 * f_target, 0.02):"
new1 = ("        # ★★★ 2026-09-28 解耦：门槛原为 `max(0.5*f_target, 0.02)` —— 当\n"
        "        #   `f_target <= 0.04` 时门槛恒为 0.02，而第一个样本落在 0.0202\n"
        "        #   ⇒ **必然不夹逼**（实测 T13b Round 49、T21 Round 28-34 同一个陷阱）。\n"
        "        #   ⇒ 去掉 0.02 地板，只留 `0.5*f_target`。\n"
        "        if f_now < 0.5 * f_target:")
assert old1 in s, 'gate not found'
s = s.replace(old1, new1)
# ③ 打印绕盒细节（T13b 的打印行原样是 '**YES**'）
old2 = "                 'ok' if s['guard'] == 'ok' else '**YES**',"
new2 = "                 s['guard'] if s['guard'] != 'ok' else 'ok',"
assert old2 in s, 'wrap print not found'
s = s.replace(old2, new2)
open(p, 'w').write(s)
ast.parse(s)
print('SYNTAX OK：门槛已解耦；绕盒细节开始打印')
print('  ⚠ 记账：跳过 reinit 的统计（原样保留）—— 见脚本内 _reinit_skipped 计数')
PYEOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T13b_verify_nv*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T13b_verify_nv.py --dx-nm 50 --ns 64,128,256 \
        --f-target 0.016 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-48
free -g | head -2
