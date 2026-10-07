#!/usr/bin/env bash
# _round21.sh --- ① 给 T24 补心跳（**不重启**：运行中的进程已加载模块，改源码只影响下次）
#                ② 用**与生产对齐的种子几何**（t=200 nm）重跑 T21
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

$PY - <<'PYEOF'
import ast
# ---- ① T24 补心跳 ----
p = 'T24_verify_grouping.py'
s = open(p).read()
old = """        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad=adv)
        if it % 5:
            continue"""
new = """        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad=adv)
        # ★★ 2026-09-28 补：**心跳**（Round 20 自查发现 T24 一直缺它 ⇒ 跑了 70 min 无法判读）
        if it % 20 == 0:
            _r0 = g.region()
            _f0 = 1.0 - float((_r0 == 0).sum()) / g.N ** 3
            print('       [心跳 T24] step=%-4d f=%.5f  步时=%.1f s  已用=%.1f min'
                  % (it, _f0, (time.time() - _t0) / it, (time.time() - _t0) / 60.0),
                  flush=True)
        if it % 5:
            continue"""
assert old in s, 'T24 loop not found'
s = s.replace(old, new)
if 'import time' not in s:
    s = s.replace('import argparse', 'import time\nimport argparse', 1)
if '_t0 = time.time()' not in s:
    s = s.replace('    out = None\n', '    out = None\n    _t0 = time.time()\n', 1)
open(p, 'w').write(s)
print('patched T24 heartbeat')

# ---- ② T21 种子厚度 → 200 nm（与生产对齐）----
p = 'T21_beta_calib.py'
s = open(p).read()
old = "0.08 * L, 100e-9, f_target)"
new = "0.08 * L, 200e-9, f_target)   # t=200 nm：与生产规格对齐（t/Δx=8）"
assert old in s, 'T21 seed_t not found'
s = s.replace(old, new)
open(p, 'w').write(s)
print('patched T21 seed_t -> 200 nm')

for f in ('T24_verify_grouping.py', 'T21_beta_calib.py'):
    ast.parse(open(f).read())
print('SYNTAX OK')
PYEOF

setsid nohup "$PY" -u T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25 \
        --betas 0,3.5,6.5 --f-target 0.05 > _t21b.log 2>&1 < /dev/null &
echo "T21b pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-58
