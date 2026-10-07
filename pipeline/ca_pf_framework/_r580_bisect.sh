#!/bin/bash
# _r580_bisect.sh --- ★ 真实路径上的**单变量二分**：找出 `E_el_J` 为何在"开关全开"下差 6.8e-01。
#
# ## 背景（必须留档）
# `_r580_smoke_cli.sh` 的 C-3 实测：5 个开关 + `pf_phi=onfly` **全开**时，
# `series.csv` 96 个共有列里 `E_el_J` 相对差 **6.814e-01**。
# 而这 6 个开关**每一个单独**都通过了逐位判据（`_r578_check.sh` / `_r579_grad.py` /
# `_r579_pfphi.py`）。⇒ 要么是**交互**，要么是**某个开关的判据没覆盖到诊断量**。
# ⇒ 只能**二分**：每个开关单独在真实路径上跑一遍，比 `series.csv`。
#
# ## 判据
#   B-1 每个"单独臂"与 BASE 的共有列最大相对差，逐个报出来（**先量后判**）；
#   B-2 若只有 `pf_phi=onfly` 单独臂就出差异 ⇒ 与其它开关**无关**，是 onfly 的语义；
#   B-3 差异列必须**点名**（不能只报一个数）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2

COMMON="--N 64 --dx-nm 62.5 --steps 30 --every 5 --snap-every 30 \
        --pair-every 30 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
        --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 --out _exp/_bk_eng"

# 臂名 => 额外 CLI
arm_cli() {
  case "$1" in
    bis_base)  echo "" ;;
    bis_eps0)  echo "--eps0-mode einsum" ;;
    bis_edp)   echo "--ed-pair gather" ;;
    bis_kloop) echo "--k-loop act" ;;
    bis_act)   echo "--act-mode bincount" ;;
    bis_arg2)  echo "--argmin2-mode copyto" ;;
    bis_grad)  echo "--grad-mode sliced" ;;
    bis_pfphi) echo "--pf-phi onfly --h-chunk 4" ;;
    bis_all)   echo "--eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly --h-chunk 4" ;;
  esac
}
ARMS="bis_base bis_eps0 bis_edp bis_kloop bis_act bis_arg2 bis_grad bis_pfphi bis_all"

echo "############ 归档改名（绝不删除）  $(date '+%F %T')"
for a in $ARMS; do
  d="_exp/_bk_eng/$a"
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)" && echo "  已改名：$d"
done

for a in $ARMS; do
  echo "############ 跑 $a : $(arm_cli "$a")"
  $PY -u _bk_exp.py $COMMON --tag "$a" $(arm_cli "$a") > "_w2_r580_${a}.log" 2>&1
  echo "  exit=$?  Traceback=$(grep -c '^Traceback' "_w2_r580_${a}.log" || true)"
  grep -m1 '算子开关' "_w2_r580_${a}.log" | sed 's/^/  /' || true
done

echo ""
echo "############ 逐臂 vs BASE 的**逐列**差异（判据：逐位相同 ⇒ 0）"
$PY - <<'PYEOF'
import os
import numpy as np
R = '_exp/_bk_eng'
ARMS = ['bis_eps0', 'bis_edp', 'bis_kloop', 'bis_act', 'bis_arg2',
        'bis_grad', 'bis_pfphi', 'bis_all']
def rd(t):
    p = os.path.join(R, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)
h0, a0 = rd('bis_base')
if a0 is None:
    print('  ❌ 缺 BASE 的 series.csv'); raise SystemExit(1)
print('  BASE: %d 列 %d 行' % (len(h0), len(np.atleast_1d(a0[h0[0]]))))
print()
print('  %-10s %-12s %s' % ('臂（单独）', '最大相对差', '差异列（>0 的全部列出）'))
print('  ' + '-' * 88)
for t in ARMS:
    h1, a1 = rd(t)
    if a1 is None:
        print('  %-10s (缺 series.csv)' % t); continue
    common = [c for c in h0 if c in h1 and c != 'wall_s']
    rows = []
    for c in common:
        x = np.atleast_1d(a0[c]).astype(float)
        y = np.atleast_1d(a1[c]).astype(float)
        m = min(len(x), len(y))
        if m == 0:
            continue
        mx = float(np.max(np.abs(x[:m])))
        d = 0.0 if mx == 0.0 else float(np.max(np.abs(x[:m] - y[:m]))) / mx
        if d != 0.0:
            rows.append((c, d))
    rows.sort(key=lambda r: -r[1])
    worst = rows[0][1] if rows else 0.0
    names = (' '.join('%s=%.2e' % (c, d) for c, d in rows[:6])
             + (' …共%d列' % len(rows) if len(rows) > 6 else '')) if rows else '（无）'
    print('  %-10s %-12.3e %s' % (t, worst, names))
print()
print('  ★ 读数规则：')
print('    · 只有 `bis_pfphi` 出差异 ⇒ 与其它开关**无关**，是 onfly 自身的语义（见下）;')
print('    · 多个单独臂都出差异 ⇒ 那些开关的单元判据**没覆盖到诊断量**，要各自补判据;')
print('    · 单独臂全 0 而 `bis_all` ≠ 0 ⇒ 是**交互**，必须定位到具体组合。')
PYEOF
echo "=== R580 BISECT DONE $(date '+%F %T') ==="
