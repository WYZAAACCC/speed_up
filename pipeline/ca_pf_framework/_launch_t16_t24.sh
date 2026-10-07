#!/usr/bin/env bash
# _launch_t16_t24.sh --- 用**同一套种子规格**（R=300 nm / t=200 nm）启动 T16 与 T24。
#   理由：t=100 nm 在 Δx=50 nm 下 `t/Δx=2` 违反约束①（板条厚必须被解析），
#   且 200 nm 更接近文献 as-built LPBF α′ 的板条厚（0.51–0.88 µm）。
#   T16：L=9.6 µm / n0=100 ⇒ d=2.068 µm ⇒ d/2R = 3.45 ✓、L/d = 4.64 ✓
#   T24：改用 L=6.4 µm（= 1.6·64^(1/3)）/ n0=64 ⇒ d=1.6 µm ⇒ d/2R = 2.67 ✓
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

$PY - <<'EOF'
import re
# T16：种子厚度 100 -> 200 nm
p = 'T16_verify_rve.py'
s = open(p).read()
s2 = s.replace('R_SEED, T_SEED = 0.30e-6, 1.0e-7',
               'R_SEED, T_SEED = 3.0e-7, 2.0e-7   # t=200 nm：约束① t/Δx≥3 且更接近文献')
assert s2 != s, 'T16 seed line not found'
open(p, 'w').write(s2)
print('patched T16')
# T24：rve() 里的种子
p = 'T24_verify_grouping.py'
s = open(p).read()
s2 = s.replace('g.seed_plate(k, c, nrm, 0.30e-6, 1.0e-7)',
               'g.seed_plate(k, c, nrm, 3.0e-7, 2.0e-7)')
assert s2 != s, 'T24 seed line not found'
open(p, 'w').write(s2)
print('patched T24')
import ast
for f in ('T16_verify_rve.py', 'T24_verify_grouping.py'):
    ast.parse(open(f).read())
print('SYNTAX OK')
EOF

setsid nohup "$PY" -u T16_verify_rve.py --L-um 9.6 --dx-nm 50 --n0 100 \
        --f-target 0.06 --adv proj2 > _t16prod.log 2>&1 < /dev/null &
echo "T16 pid=$!"
setsid nohup "$PY" -u T24_verify_grouping.py --mode rve --L-um 6.4 --dx-nm 50 \
        --n0 64 --f-target 0.06 --adv proj2 > _t24rve.log 2>&1 < /dev/null &
echo "T24 pid=$!"
sleep 25
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-60
free -g | head -2
