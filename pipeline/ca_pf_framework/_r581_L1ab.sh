#!/bin/bash
# _r581_L1ab.sh --- ★ L1（`--extend-mode`）的**真实路径 A/B**：逐位 + 配对提速。
#
# ## 这一步是什么门
# goal §(2) 的**门 4**：真实 `_bk_exp.py` 算例，**全部落盘列**逐位一致、无 Traceback。
# （R580 实测过：`onfly` 起初对 `g.phi` 逐位等价，却让诊断量 `E_el_J` 差 3.1×
#   ⇒ **门 4 必须比"全部落盘列"**，不能只比 `g.phi`。）
#
# ## 口径
#   * 3 臂：`legacy`（归档旧路）/ `merged`（EDT 合一）/ `near`（+ 只在 near 上 gather）
#   * **轮换 + 交错**：每轮里 3 臂的顺序按轮次偏移（`R579_quiet_ab.sh` 同纪律）。
#   * **每轮一个独立目录**（`_exp/_bk_l1/r<N>`）⇒ 配对是**同轮内**的，抗宿主漂移。
#   * ⚠ **不设 `MALLOC_*`**（AGENTS P7：那档实测慢 1.64×，会和被测项混在一起）。
#   * 开关档 = **生产意图档**（7 开关 + f32 + onfly）⇒ 量的是真实要用的配置。
#   * 判据：`series.csv` 的**全部共有列**（除 `wall_s`）逐位相同（`d == 0.0`）。
#     ⚠ 用 `R580` 修正过的口径：NaN 列单独归类，不用 `d > worst`（那个写法会**静默跳过 NaN 列**）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

N="${R581L1_N:-64}"
STEPS="${R581L1_STEPS:-30}"
ROUNDS="${R581L1_ROUNDS:-4}"
WORK="${R581L1_WORKERS:-4}"
ROOT="_exp/_bk_l1"
LOG=_w2_r581_L1ab.log
: > "$LOG"

PROD="--eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount \
      --argmin2-mode copyto --grad-mode sliced --pf-phi onfly --h-chunk 4 \
      --phi-prec f32"
COMMON="--N $N --dx-nm 62.5 --steps $STEPS --every 1 --snap-every 99999 \
        --pair-every 0 --norm-smooth 0 --nthreads $WORK --reinit-dt 1e-4 \
        --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 8 \
        --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
        --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
        --cool-rate 2.3524e6 --plate-L 1000 --plate-W 500 --plate-T 510 \
        --gamma0 0.25 --beta-h 6.477 --facet-proj 0 --facet-excl 0"

arm_cli() {
  case "$1" in
    legacy) echo "--extend-mode legacy" ;;
    merged) echo "--extend-mode merged" ;;
    near)   echo "--extend-mode near" ;;
  esac
}

echo "=== R581-L1 真实路径 A/B（3 臂 × $ROUNDS 轮，轮换）N=$N steps=$STEPS w=$WORK ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"
echo "  ⚠ 不设 MALLOC_*（PLAIN 口径）；开关档 = 生产意图档（7 开关 + f32 + onfly）" | tee -a "$LOG"

ARMS=(legacy merged near)
NA=${#ARMS[@]}
for r in $(seq 1 "$ROUNDS"); do
  OUT="$ROOT/r$r"
  echo "---- round $r（偏移 $(( (r-1) % NA ))）----" | tee -a "$LOG"
  # 归档改名（绝不删除）
  for a in "${ARMS[@]}"; do
    d="$OUT/dry_$a"
    [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
  done
  for i in $(seq 0 $((NA-1))); do
    a="${ARMS[$(( (i + (r-1)) % NA ))]}"
    LGF="_w2_r581_L1ab_${a}_r${r}.log"
    taskset -c 8-15 $PY -u _bk_exp.py $COMMON $PROD --out "$OUT" --tag "$a" \
        $(arm_cli "$a") > "$LGF" 2>&1
    RC=$?
    TB=$(grep -c '^Traceback' "$LGF" || true)
    SW=$(grep -m1 '算子开关' "$LGF" | sed 's/.*算子开关：//' | cut -c1-70)
    echo "  r$r $a exit=$RC Traceback=$TB  [$SW]" | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "############ 门 4：全部共有列**逐位**比对（同轮内配对）" | tee -a "$LOG"
$PY - "$ROOT" "$ROUNDS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, re, statistics, sys
import numpy as np
ROOT, ROUNDS = sys.argv[1], int(sys.argv[2])
RE_STEP = re.compile(r'\[(\s*\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')
ARMS = ['legacy', 'merged', 'near']

def rd(rr, t):
    p = os.path.join(ROOT, 'r%d' % rr, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)

def sstep(rr, t):
    p = '_w2_r581_L1ab_%s_r%d.log' % (t, rr)
    if not os.path.exists(p):
        return []
    txt = open(p, errors='replace').read()
    v = [float(m.group(3)) for m in RE_STEP.finditer(txt)]
    return v[-4:] if len(v) >= 4 else v

h0, a0 = rd(1, 'legacy')
if a0 is None:
    print('  ❌ 缺 r1/legacy 的 series.csv'); raise SystemExit(1)
print('  BASE(legacy): %d 列' % len(h0))
print()
print('  %-8s %-26s %s' % ('轮', '臂', '逐位比对（共有列，排除 wall_s）'))
print('  ' + '-' * 92)
tot_fail = 0
for rr in range(1, ROUNDS + 1):
    h0, a0 = rd(rr, 'legacy')
    if a0 is None:
        print('  r%-7d (缺 legacy)' % rr); continue
    for t in ('merged', 'near'):
        h1, a1 = rd(rr, t)
        if a1 is None:
            print('  r%-7d %-26s (缺 series.csv)' % (rr, t)); tot_fail += 1; continue
        common = [c for c in h0 if c in h1 and c != 'wall_s']
        nfin = nboth_nan = nposdiff = 0
        real = []
        for c in common:
            x = np.atleast_1d(a0[c]).astype(float)
            y = np.atleast_1d(a1[c]).astype(float)
            m = min(len(x), len(y))
            if m == 0:
                continue
            x, y = x[:m], y[:m]
            mx_ = np.isfinite(x); my_ = np.isfinite(y)
            both = mx_ & my_
            if both.any():
                nfin += 1
            else:
                nboth_nan += 1
                continue
            if np.array_equal(x[both], y[both]):
                continue
            if np.array_equal(mx_, my_):
                real.append(c)
            else:
                nposdiff += 1
        tag = ('✅ 逐位（%d 有限列 / %d 全NaN列）' % (nfin, nboth_nan)
               if not real and not nposdiff else
               '❌ 真有差异 %d 列 %s / nan位置不同 %d' % (len(real), real[:4], nposdiff))
        if real or nposdiff:
            tot_fail += 1
        print('  r%-7d %-26s %s' % (rr, t, tag))
print()
print('  ⇒ 门 4 判定：%s' % ('✅ PASS（全部轮次、全部共有列逐位一致）'
                        if tot_fail == 0 else '❌ FAIL（%d 处）' % tot_fail))

# ---- 配对提速 -------------------------------------------------------------
print()
print('############ 配对提速（同轮 legacy/arm，交错轮换）')
med = {}
for t in ARMS:
    per = []
    for rr in range(1, ROUNDS + 1):
        a = sstep(rr, 'legacy'); b = sstep(rr, t)
        if a and b:
            per.append(statistics.mean(a) / statistics.mean(b))
    med[t] = per
    if per:
        print('  %-8s 每轮提速 = %s ⇒ **中位 %.3f×**  区间 [%.3f, %.3f]'
              % (t, ['%.3f' % x for x in per], statistics.median(per),
                 min(per), max(per)))
    else:
        print('  %-8s ⚠ 无有效读数' % t)
PYEOF
echo "=== R581 L1 A/B DONE $(date '+%F %T') ===" | tee -a "$LOG"
