#!/usr/bin/env bash
# _round32.sh --- T21 夹逼的**第三次（也是最终）修法**：在循环**之前**先采一次种子态。
#   前两次都失败的实测原因：`f` 在**第 1 步之后**就已经是 1.78e-3（种子分数之上），
#   而任何 `f_ar_ref` 只要 > 1.78e-3 就永远夹不住。⇒ **必须把"种子态"本身作为一个采样点**，
#   这样任何 `f_ar_ref > f_seed` 都必然被 `[f_seed, f(1)]` 夹住。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
import ast
p = 'T21_beta_calib.py'
s = open(p).read()
old = """    for it in range(1, steps_max + 1):
        g.elastic_driving()"""
new = """    # ★★★ 2026-09-28 第三次（最终）修法：**先把种子态本身采一个点**。
    #   实测：`f` 在第 1 步之后就已经是 1.78e-3（种子分数 1.12e-3 之上）
    #   ⇒ 不采种子态的话，**任何** `f_ar_ref > 1.78e-3` 都永远夹不住（前两次都栽在这里）。
    _ar0, _f0_ = _ar_now()
    if np.isfinite(_ar0):
        traj.append((_f0_, _ar0))
    print('       [轨迹 β=%.1f] step=0(种子) f=%.5f AR=%.3f' % (beta, _f0_, _ar0),
          flush=True)
    for it in range(1, steps_max + 1):
        g.elastic_driving()"""
assert old in s, 'loop head not found'
s = s.replace(old, new, 1)
open(p, 'w').write(s)
ast.parse(s)
print('SYNTAX OK：已加"种子态采样点"')
EOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T21_beta_calib*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25 \
        --betas 0,1.5,3.5,6.5 --f-target 0.05 > _t21f.log 2>&1 < /dev/null &
echo "T21f pid=$!"
sleep 25
grep -E '轨迹' _t21f.log | head -4
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-50
