#!/bin/bash
# _r578_smoke.sh --- R578：`--k-loop act` 的**真实路径**冒烟（含逐位判据）。
#
# 判据（先写死）：
#   S-1 两臂 exit 0、Traceback = 0；
#   S-2 `act` 臂的 banner 必须**列出** `k_loop=act`（防"改了但输出里没标识"）；
#   S-3 两臂 `series.csv` **共有列逐位一致**（`act` 是逐位等价的改动 ⇒ 要求 0）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
# ⚠ R577 实测：这三个变量让引擎慢 1.64×。本冒烟**刻意保留**它们（= 仓库大多数脚本的口径），
#   以便与归档的 `_r569_smoke.sh` 产物可比；k_loop 的**墙钟**另由 `_r578_kloop_ab.sh` 量。
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2

COMMON="--N 64 --dx-nm 62.5 --steps 30 --every 5 --snap-every 30 \
        --pair-every 30 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
        --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 --out _exp/_bk_eng"

echo "############ 归档改名（绝不删除）  $(date '+%F %T')"
for d in _exp/_bk_eng/r578_full _exp/_bk_eng/r578_act; do
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)" && echo "  已改名：$d"
done

echo "############ S-1a FULL（归档旧路）"
$PY -u _bk_exp.py $COMMON --tag r578_full > _w2_r578_full.log 2>&1
echo "  exit=$?  traceback=$(grep -c 'Traceback' _w2_r578_full.log || true)"
grep -m1 '算子开关' _w2_r578_full.log || echo "  **没看到开关 banner**"
tail -2 _w2_r578_full.log

echo "############ S-1b ACT（--k-loop act）"
$PY -u _bk_exp.py $COMMON --tag r578_act --k-loop act > _w2_r578_act.log 2>&1
echo "  exit=$?  traceback=$(grep -c 'Traceback' _w2_r578_act.log || true)"
grep -m1 '算子开关' _w2_r578_act.log || echo "  **没看到开关 banner**"
tail -2 _w2_r578_act.log

echo "############ S-2 banner 必须列出 k_loop=act"
if grep -q 'k_loop=act' _w2_r578_act.log; then
  echo "  ✅ PASS"
else
  echo "  ❌ FAIL：act 臂的 banner 里没有 k_loop=act"
fi

echo "############ S-3 共有列逐位一致"
$PY - <<'PYEOF'
import os
import numpy as np
R = '_exp/_bk_eng'
bad = False
for col in ('r578_full', 'r578_act'):
    p = os.path.join(R, 'dry_' + col, 'series.csv')
    if not os.path.exists(p):
        print('  ❌ 缺文件：%s' % p); bad = True
if not bad:
    def rd(t):
        p = os.path.join(R, 'dry_' + t, 'series.csv')
        with open(p) as fh:
            return fh.readline().strip().split(','), p
    h1, p1 = rd('r578_full')
    h2, p2 = rd('r578_act')
    a1 = np.genfromtxt(p1, delimiter=',', names=True)
    a2 = np.genfromtxt(p2, delimiter=',', names=True)
    common = [c for c in h1 if c in h2 and c != 'wall_s']
    worst, wc = 0.0, None
    for c in common:
        x = np.atleast_1d(a1[c]).astype(float)
        y = np.atleast_1d(a2[c]).astype(float)
        m = min(len(x), len(y))
        if m == 0:
            continue
        mx = float(np.max(np.abs(y[:m])))
        d = 0.0 if mx == 0.0 else float(np.max(np.abs(x[:m] - y[:m]))) / mx
        if d > worst:
            worst, wc = d, c
    print('  共有列 %d 个；最大相对差 = %.3e（%s）⇒ %s'
          % (len(common), worst, wc, '✅ 逐位一致' if worst == 0.0 else '❌ 有差异'))
PYEOF
echo "=== R578 SMOKE DONE $(date '+%F %T') ==="
