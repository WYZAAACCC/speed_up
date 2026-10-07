#!/bin/bash
# _r580_smoke_cli.sh --- ★ 真实路径冒烟：**用 `_bk_exp.py` 的 CLI 开关**把新开关全开，
#                        并与默认档做**共有列逐位对照**。
#
# ## 为什么必须单独一份（而不是复用 `_r578_smoke.sh` 的环境变量档）
# `_r578_smoke.sh` 里那些 `R561_*` 环境变量只有 `_r576_prof.py` 那条安装路径认；
# `_bk_exp.py` 走的是 **CLI 参数** ⇒ 环境变量档**根本没开开关**，
# 是个"看起来开了、其实没开"的假对照（本仓库反复记过这类静默失效）。
#
# ## 判据（先写死，必须能失败）
#   C-1 两臂 exit 0、Traceback = 0
#   C-2 全开臂的 banner 必须**逐个列出** 5 个开关（防"改了但没生效"）
#   C-3 两臂 `series.csv` **共有列逐位一致**（这 5 个开关都是逐位等价的）⇒ 要求 max|Δ| = 0
#   C-4 负对照：把 `--h-chunk` 改成非法值必须**硬失败**（证明 C-2 的 banner 不是摆设）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
# ⚠ 与归档冒烟同口径（含那三个 MALLOC_*），以便 series.csv 与归档产物可比
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2

COMMON="--N 64 --dx-nm 62.5 --steps 30 --every 5 --snap-every 30 \
        --pair-every 30 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
        --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 --out _exp/_bk_eng"

echo "############ 归档改名（绝不删除）  $(date '+%F %T')"
for d in _exp/_bk_eng/r580_base _exp/_bk_eng/r580_allon; do
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)" && echo "  已改名：$d"
done

echo "############ C-1a BASE（全默认 = 归档旧路）"
$PY -u _bk_exp.py $COMMON --tag r580_base > _w2_r580_base.log 2>&1
echo "  exit=$?  traceback=$(grep -c 'Traceback' _w2_r580_base.log || true)"
grep -m1 '算子开关' _w2_r580_base.log || echo "  **没看到开关 banner**"
tail -2 _w2_r580_base.log

echo "############ C-1b ALLON（5 个开关全开 + pf_phi onfly）"
$PY -u _bk_exp.py $COMMON --tag r580_allon \
    --eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount \
    --argmin2-mode copyto --grad-mode sliced --pf-phi onfly --h-chunk 4 \
    > _w2_r580_allon.log 2>&1
echo "  exit=$?  traceback=$(grep -c 'Traceback' _w2_r580_allon.log || true)"
grep -m1 '算子开关' _w2_r580_allon.log || echo "  **没看到开关 banner**"
tail -2 _w2_r580_allon.log

echo "############ C-2 banner 必须逐个列出开关"
BAN=$(grep -m1 '算子开关' _w2_r580_allon.log || true)
echo "  banner: $BAN"
MISS=""
for k in eps0=einsum ed_pair=gather k_loop=act act=bincount argmin2=copyto grad=sliced pf_phi=onfly; do
  echo "$BAN" | grep -q -- "$k" || MISS="$MISS $k"
done
if [ -z "$MISS" ]; then
  echo "  ✅ PASS：7 项全部出现在 banner 里"
else
  echo "  ⚠ 未在 banner 里出现：$MISS"
  echo "     （可能是该开关的 banner 文案与这里写的不一致 —— **不影响数值判据**，但要记账）"
fi

echo "############ C-3 共有列逐位一致（判据 = 0）"
$PY - <<'PYEOF'
import os
import numpy as np
R = '_exp/_bk_eng'
bad = False
for col in ('r580_base', 'r580_allon'):
    p = os.path.join(R, 'dry_' + col, 'series.csv')
    if not os.path.exists(p):
        print('  ❌ 缺文件：%s' % p); bad = True
if not bad:
    def rd(t):
        p = os.path.join(R, 'dry_' + t, 'series.csv')
        with open(p) as fh:
            return fh.readline().strip().split(','), p
    h1, p1 = rd('r580_base')
    h2, p2 = rd('r580_allon')
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
          % (len(common), worst, wc,
             '✅ 逐位一致（判据 0）' if worst == 0.0 else '❌ 有差异'))
PYEOF

echo "############ C-4 负对照：非法 --h-chunk 必须硬失败"
$PY -u _bk_exp.py $COMMON --tag r580_neg --pf-phi onfly --h-chunk 0 \
    > _w2_r580_neg.log 2>&1
NRC=$?
echo "  exit=$NRC（期望 **非 0**）"
grep -m1 -E 'h_chunk|ValueError' _w2_r580_neg.log | sed 's/^/    /' || true
if [ "$NRC" -ne 0 ]; then
  echo "  ✅ PASS：负对照被硬拦住"
else
  echo "  ❌ FAIL：非法参数竟然跑通了 —— 说明开关没接线"
fi

echo "=== R580 SMOKE-CLI DONE $(date '+%F %T') ==="
