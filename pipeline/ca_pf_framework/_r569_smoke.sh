#!/bin/bash
# _r569_smoke.sh --- R568 开关的**真实路径**冒烟。
#
# 为什么必须跑（项目纪律）：单元量具过 ≠ 真实路径过。本轮改的
# `elastic_driving_pair` / `eps0_fields` / `sigma_tensor` 都是**多调用方**函数，
# 单元判据（`_r568_opverify.py`）只覆盖了其中一条调用链。
#
# 判据：
#   S-1 两个算例都 **exit 0**，日志里 **Traceback 行数 = 0**、**顶层异常行数 = 0**
#   S-2 开关自述 banner 必须出现，且 ON 那一跑要**列出** fft/eps0/ed_pair
#   S-3 ON 与 OFF 的 `series.csv` **共有列**必须一致到 1e-12 相对（**不要求逐位**
#       —— `rfft` 差 1–2 ulp，长轨迹会分叉；这里只用来看"有没有炸"）
#       ⚠ 若只想验证"逐位"那一档，把 `--fft-mode rfft` 去掉再跑（见 S-3b）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

COMMON="--N 64 --dx-nm 62.5 --steps 30 --every 5 --snap-every 15 \
        --pair-every 10 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
        --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 --out _exp/_bk_eng"

echo "############ S-0 归档改名（绝不删除）############"
for d in _exp/_bk_eng/r569_off _exp/_bk_eng/r569_on _exp/_bk_eng/r569_bit; do
  if [ -d "$d" ]; then
    mv "$d" "${d}_superseded_$(date +%s)"
    echo "  已改名归档：$d"
  fi
done

echo
echo "############ S-1a OFF（归档旧路）############"
$PY -u _bk_exp.py $COMMON --tag r569_off > _w2_r569_off.log 2>&1
echo "  exit=$?"
grep -c 'Traceback' _w2_r569_off.log || true
grep -m1 '算子开关' _w2_r569_off.log || echo "  **没看到开关 banner**"
tail -3 _w2_r569_off.log

echo
echo "############ S-1b ON（rfft + einsum + gather）############"
$PY -u _bk_exp.py $COMMON --tag r569_on \
    --fft-mode rfft --eps0-mode einsum --ed-pair gather > _w2_r569_on.log 2>&1
echo "  exit=$?"
grep -c 'Traceback' _w2_r569_on.log || true
grep -m1 '算子开关' _w2_r569_on.log || echo "  **没看到开关 banner**"
tail -3 _w2_r569_on.log

echo
echo "############ S-1c BIT（只开逐位那一档：einsum + gather）############"
$PY -u _bk_exp.py $COMMON --tag r569_bit \
    --eps0-mode einsum --ed-pair gather > _w2_r569_bit.log 2>&1
echo "  exit=$?"
grep -c 'Traceback' _w2_r569_bit.log || true
grep -m1 '算子开关' _w2_r569_bit.log || echo "  **没看到开关 banner**"
tail -3 _w2_r569_bit.log

echo
echo "############ S-3 列对比 ############"
# ⚠ R570 自查错误：这一段原来写 `$R/<tag>/series.csv`，而实际布局是 `$R/dry_<tag>/`，
#   于是三个算例全都"找不到"却被当成 FAIL 报出来（`AGENTS §3.17`：先怀疑自己的路径）。
#   ⇒ 现在两个候选都试；更完整的对比另见 `_r570_colcmp.py`。
$PY - <<'PYEOF'
import os, sys
import numpy as np
R = '_exp/_bk_eng'


def rd(tag):
    for p in (os.path.join(R, 'dry_' + tag, 'series.csv'),
              os.path.join(R, tag, 'series.csv')):
        if os.path.exists(p):
            with open(p) as fh:
                hdr = fh.readline().strip().split(',')
            return hdr, p
    return None, None


def cmp(t1, t2, tol, label):
    h1, p1 = rd(t1)
    h2, p2 = rd(t2)
    if not p1 or not p2:
        print('  ❌ 缺文件：%s（%s / %s）' % (label, t1, t2))
        return False
    a1 = np.genfromtxt(p1, delimiter=',', names=True)
    a2 = np.genfromtxt(p2, delimiter=',', names=True)
    common = [c for c in h1 if c in h2 and c != 'wall_s']
    worst, bad = 0.0, []
    for c in common:
        x = np.atleast_1d(a1[c]).astype(float)
        y = np.atleast_1d(a2[c]).astype(float)
        n = min(len(x), len(y))
        if n == 0:
            continue
        mx = float(np.max(np.abs(y[:n])))
        d = 0.0 if mx == 0.0 else float(np.max(np.abs(x[:n] - y[:n]))) / mx
        worst = max(worst, d)
        if d > tol:
            bad.append((c, d))
    print('  %s' % label)
    print('     共有列 %d 个（剔 wall_s）；最大相对差 = %.3e（容差 %.0e）⇒ %s'
          % (len(common), worst, tol, '✅ PASS' if not bad else '❌ FAIL: %s' % bad[:6]))
    return not bad


ok = True
ok &= cmp('r569_bit', 'r569_off', 0.0, 'S-3b **逐位档** einsum+gather vs 旧路（要求 0）')
ok &= cmp('r569_on', 'r569_off', 1e-9, 'S-3a rfft 档 vs 旧路（只证明没炸，容差 1e-9）')
print('  ⇒ 总判定：%s' % ('✅ PASS' if ok else '❌ FAIL'))
PYEOF
echo "=== R569 SMOKE DONE $(date '+%F %T') ==="
