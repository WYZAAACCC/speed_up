#!/bin/bash
# _r581_final_ab.sh --- ★★ goal §(10)② / 成功判据⑦：**"能开尽开 vs 全默认"的配对提速**。
#
# ## 为什么这个实验特别有说服力
# 本轮所有开关都被判过**逐位相同**（四道门）⇒ 两臂的 `series.csv` 必须**逐位一致**。
# 所以"提速"是**纯粹的**：同样的物理、同样的数，只是跑得更快。
# ⇒ 本脚本**同时**给两样东西：
#   ① 配对提速（≥5 轮、轮换、报区间）；
#   ② **全部共有列逐位一致**（否则提速无意义）。
#
# ## 口径
#   * 参考配置 = 归档基准那一档（N=64 / nv=24 / dx=62.5 nm / 4 线程），
#     这样 BASE 可与历史读数（0.2814 s/步）对上量级。
#   * 不设 `MALLOC_*`（AGENTS P7：那档慢 1.64×，会与开关混在一起）。
#   * 轮换 + 交错；每轮独立目录。
#   * ⚠ 本机此刻**不是安静机器**（两个 N=160 长跑在跑）⇒ 绝对值不可比历史，
#     但**配对比值**在同一轮内仍然有效（两臂看到同一个背景负载）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

N="${R581F_N:-64}"
NV="${R581F_NV:-24}"
STEPS="${R581F_STEPS:-12}"
ROUNDS="${R581F_ROUNDS:-5}"
CORES="${R581F_CORES:-8-15}"
ROOT="_exp/_bk_final"
LOG=_w2_r581_final.log
: > "$LOG"

# 归档默认档：**一个开关都不开**
BASE_ARG=""
# 「能开尽开」：P-13 的 7 项 + 本轮 L1/L2/L4/L5/L6（**全部逐位相同**）
ALL_ARG="--eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount \
         --argmin2-mode copyto --grad-mode sliced --pf-phi onfly --h-chunk 4 \
         --extend-mode near --eps0-tile 4 --argmin2-reuse 1 --bbox-mode axis \
         --ufv-c 1"

COMMON="--N $N --dx-nm 62.5 --steps $STEPS --every 1 --snap-every 99999 \
        --pair-every 0 --norm-smooth 0 --nthreads 4 --reinit-dt 1e-4 \
        --nuc-overlap-nm 62.5 --nuc-law athermal --nuc-init 6 \
        --nuc-block-target 5 --nuc-shape ellipsoid --nuc-supercrit 1 \
        --nuc-sites-refill 1 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 \
        --T-end 350.0 --cool-rate 2.3524e6 --plate-L 1000 --plate-W 500 \
        --plate-T 510 --gamma0 0.25 --beta-h 6.477 --grow-stack \
        --facet-proj 0 --facet-excl 0 --laths 1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12"

echo "=== R581 收口实验：能开尽开 vs 全默认（$ROUNDS 轮 × N=$N nv=$NV）===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"
echo "  ⚠ 非安静机器（两个 N=160 长跑在跑）⇒ 只信**配对**比值，不信绝对值" | tee -a "$LOG"

for r in $(seq 1 "$ROUNDS"); do
  OUT="$ROOT/r$r"
  echo "---- round $r ----" | tee -a "$LOG"
  for a in BASE ALL; do
    d="$OUT/dry_$a"
    [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
  done
  # 交错 + 轮换
  if [ $((r % 2)) -eq 0 ]; then ORDER="ALL BASE"; else ORDER="BASE ALL"; fi
  for a in $ORDER; do
    if [ "$a" = BASE ]; then ARG="$BASE_ARG"; else ARG="$ALL_ARG"; fi
    LGF="_w2_r581_final_${a}_r${r}.log"
    taskset -c "$CORES" $PY -u _bk_exp.py $COMMON --out "$OUT" --tag "$a" $ARG \
        > "$LGF" 2>&1
    SW=$(grep -m1 '算子开关' "$LGF" | sed 's/.*算子开关：//' | cut -c1-100)
    echo "  r$r $a exit=$? Traceback=$(grep -c '^Traceback' "$LGF" || true)  [$SW]" \
        | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "############ ① 全部共有列**逐位**（这是"提速是纯的"的证明）" | tee -a "$LOG"
$PY - "$ROOT" "$ROUNDS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, re, statistics, sys
import numpy as np
ROOT, ROUNDS = sys.argv[1], int(sys.argv[2])
RE_STEP = re.compile(r'\[\s*(\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')

def rd(rr, t):
    p = os.path.join(ROOT, 'r%d' % rr, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)

def sstep(rr, t):
    p = '_w2_r581_final_%s_r%d.log' % (t, rr)
    if not os.path.exists(p):
        return []
    v = [float(m.group(3)) for m in RE_STEP.finditer(open(p, errors='replace').read())]
    return v[-4:] if len(v) >= 4 else v

tot = 0
for rr in range(1, ROUNDS + 1):
    h0, a0 = rd(rr, 'BASE'); h1, a1 = rd(rr, 'ALL')
    if a0 is None or a1 is None:
        print('  r%-3d ❌ 缺 series.csv' % rr); tot += 1; continue
    common = [c for c in h0 if c in h1 and c != 'wall_s']
    nfin = nnan = npos = 0; real = []
    for c in common:
        x = np.atleast_1d(a0[c]).astype(float); y = np.atleast_1d(a1[c]).astype(float)
        m = min(len(x), len(y))
        if m == 0: continue
        x, y = x[:m], y[:m]
        fx, fy = np.isfinite(x), np.isfinite(y); both = fx & fy
        if not both.any(): nnan += 1; continue
        nfin += 1
        if np.array_equal(x[both], y[both]): continue
        if np.array_equal(fx, fy): real.append(c)
        else: npos += 1
    ok = (not real) and (not npos)
    tot += 0 if ok else 1
    print('  r%-3d %s（%d 有限列 / %d 全NaN列）%s'
          % (rr, '✅ 逐位一致' if ok else '❌ 有差异 %s / nan位置不同 %d' % (real[:4], npos),
             nfin, nnan, ''))
print('  ⇒ 判据：%s' % ('✅ 全部轮次逐位一致 ⇒ **提速是纯的**' if tot == 0
                    else '❌ %d 处差异 ⇒ 提速不可信' % tot))

print()
print('############ ② 配对提速（同轮内 BASE/ALL，交错 + 轮换）')
ratios = []
for rr in range(1, ROUNDS + 1):
    a, b = sstep(rr, 'BASE'), sstep(rr, 'ALL')
    if a and b:
        ra = statistics.mean(a); rb = statistics.mean(b)
        ratios.append(ra / rb)
        print('  r%-3d BASE 末4中位 %8.4f s/步    ALL %8.4f s/步   ⇒ **%.3f×**'
              % (rr, statistics.median(a), statistics.median(b), ra / rb))
    else:
        print('  r%-3d ⚠ 无有效读数' % rr)
if ratios:
    print()
    print('  ⇒ **"能开尽开 vs 全默认" 配对提速 = %.3f×**   区间 [%.3f, %.3f]'
          % (statistics.median(ratios), min(ratios), max(ratios)))
    n_gt1 = sum(1 for x in ratios if x > 1.0)
    print('  ⇒ %d/%d 轮 > 1（判据：全部轮次 > 1 才算确立）' % (n_gt1, len(ratios)))
PYEOF
echo "=== R581 FINAL AB DONE $(date '+%F %T') ===" | tee -a "$LOG"
