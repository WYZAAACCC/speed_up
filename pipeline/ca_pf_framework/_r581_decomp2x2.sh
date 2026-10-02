#!/bin/bash
# _r581_decomp2x2.sh --- ★★ goal §(10)①：**2×2 构成分解**
#   「检查"两项相乘 vs 实测全开"是否一致（不一致要记账，不许强行解释）」
#
# ## 为什么必须做这个（而不是只看"全开 vs 全默认"）
# `R581_OPOPT_L1L2.md §19.3` 记了一条：各车道的"省单步 %"**相加 ≈42%**，
# 而整步配对实测只有 **1.232×**。两者对不上。**但"相加"本来就只是个粗模型。**
# 本实验用**最干净的 2×2**回答一个更精确的问题：
#   **两个开关的收益是"相乘"（互相独立）还是"次相乘"（互相争同一份资源）？**
#
# ## 选哪两个开关
# 取**整步效应最大**的两个（各自都做过整步配对）：
#   * `--eps0-tile 4`  （L2）整步 **1.178×**
#   * `--ufv-c 1`      （L6）整步 **1.190×**
# 若互相独立 ⇒ `11` 应为 **1.178 × 1.190 = 1.402×**。
#
# ## 判据（**预先写死**）
#   | r11 / (r10·r01) − 1 | ≤ 0.05  ⇒ **相乘成立**（独立）
#   < −0.05                          ⇒ **次相乘**（争资源）—— 要记账，不许解释成"正常"
#   > +0.05                          ⇒ 超相乘（少见，要查）
#
# ## 另外（免费但很值钱）
# 四个臂都只开**逐位**开关 ⇒ 四份 `series.csv` 的**全部共有列必须逐位一致**。
# 这同时是「§(2) 门 1 逐位」在 **4 个组合**上的复验。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
N="${R581D2_N:-64}"
NV="${R581D2_NV:-24}"
STEPS="${R581D2_STEPS:-12}"
ROUNDS="${R581D2_ROUNDS:-4}"
CORES="${R581D2_CORES:-12-15}"
ROOT="_exp/_bk_d2"
LOG=_w2_r581_d2.log
: > "$LOG"

COMMON="--N $N --dx-nm 62.5 --steps $STEPS --every 1 --snap-every 99999 \
        --pair-every 0 --norm-smooth 0 --nthreads 4 --reinit-dt 1e-4 \
        --nuc-overlap-nm 62.5 --nuc-law athermal --nuc-init 6 \
        --nuc-block-target 5 --nuc-shape ellipsoid --nuc-supercrit 1 \
        --nuc-sites-refill 1 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 \
        --T-end 350.0 --cool-rate 2.3524e6 --plate-L 1000 --plate-W 500 \
        --plate-T 510 --gamma0 0.25 --beta-h 6.477 --grow-stack \
        --facet-proj 0 --facet-excl 0 \
        --laths 1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12 \
        --eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount \
        --argmin2-mode copyto --grad-mode sliced --pf-phi onfly --h-chunk 4 \
        --extend-mode near --argmin2-reuse 1 --bbox-mode axis"

echo "=== R581 2×2 构成分解（$ROUNDS 轮 × N=$N nv=$NV）===" | tee -a "$LOG"
$PY _r576_hostfp.py 2>/dev/null | sed 's/^/  /' | tee -a "$LOG"
echo "  臂：00=既不 tile 也不 ufv-c / 10=只 tile4 / 01=只 ufv-c / 11=两个都开" | tee -a "$LOG"
echo "  ⚠ 本机此刻还有两个 N=160 长跑在跑 ⇒ 只信**同轮配对**的比值" | tee -a "$LOG"

for r in $(seq 1 "$ROUNDS"); do
  [ "${R581D2_ANALYZE_ONLY:-0}" = "1" ] && break
  echo "---- round $r ----" | tee -a "$LOG"
  # 轮换顺序（4 个臂 ⇒ 每次左移）
  case $((r % 4)) in
    1) ORD="00 10 01 11" ;;
    2) ORD="10 01 11 00" ;;
    3) ORD="01 11 00 10" ;;
    0) ORD="11 00 10 01" ;;
  esac
  for a in $ORD; do
    case "$a" in
      00) EXTRA="" ;;
      10) EXTRA="--eps0-tile 4" ;;
      01) EXTRA="--ufv-c 1" ;;
      11) EXTRA="--eps0-tile 4 --ufv-c 1" ;;
    esac
    d="$ROOT/r$r/dry_$a"
    [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
    LGF="_w2_r581_d2_${a}_r${r}.log"
    taskset -c "$CORES" $PY -u _bk_exp.py $COMMON --out "$ROOT/r$r" --tag "$a" $EXTRA \
        > "$LGF" 2>&1
    echo "  r$r $a exit=$? Traceback=$(grep -c '^Traceback' "$LGF" || true)" | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "############ ① 四个臂的 series.csv 必须**逐位一致**（都只开逐位开关）" | tee -a "$LOG"
$PY - "$ROOT" "$ROUNDS" "$N" "$STEPS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, re, statistics, sys
import numpy as np
ROOT, ROUNDS, NCONF, STEPS = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
RE = re.compile(r'\[\s*(\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')
ARMS = ['00', '10', '01', '11']

def rd(rr, t):
    p = os.path.join(ROOT, 'r%d' % rr, 'dry_' + t, 'series.csv')
    if not os.path.exists(p): return None, None
    with open(p) as fh: h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)

def sp(rr, t):
    p = '_w2_r581_d2_%s_r%d.log' % (t, rr)
    if not os.path.exists(p): return []
    v = [float(m.group(3)) for m in RE.finditer(open(p, errors='replace').read())]
    return v[-4:] if len(v) >= 4 else v

bad = 0
for rr in range(1, ROUNDS + 1):
    hs, ds = {}, {}
    for a in ARMS:
        h, d = rd(rr, a)
        if h is None: continue
        hs[a], ds[a] = h, d
    if '00' not in hs:
        print('  r%-3d ❌ 缺基准臂 00' % rr); bad += 1; continue
    base = hs['00']
    msgs = []
    for a in ARMS[1:]:
        if a not in hs: continue
        common = [c for c in base if c in hs[a] and c != 'wall_s']
        nreal = 0
        for c in common:
            x = np.atleast_1d(ds['00'][c]).astype(float)
            y = np.atleast_1d(ds[a][c]).astype(float)
            m = min(len(x), len(y)); x, y = x[:m], y[:m]
            b = np.isfinite(x) & np.isfinite(y)
            if b.any() and not np.array_equal(x[b], y[b]): nreal += 1
        msgs.append('%s:%s(%d列)' % (a, '✅' if nreal == 0 else '❌%d' % nreal, len(common)))
        bad += (nreal != 0)
    print('  r%-3d %s' % (rr, '  '.join(msgs)))
print('  ⇒ %s' % ('✅ 四个臂逐位一致' if bad == 0 else '❌ %d 处差异' % bad))

print()
print('############ ② 2×2 分解：实测 vs "两项相乘"')
tab = {}
for rr in range(1, ROUNDS + 1):
    row = {}
    for a in ARMS:
        v = sp(rr, a)
        if v: row[a] = statistics.mean(v)
    if len(row) == 4:
        tab[rr] = row
        r10 = row['00'] / row['10']; r01 = row['00'] / row['01']; r11 = row['00'] / row['11']
        pred = r10 * r01
        print('  r%-3d  t00=%.4f  r10=%.3f  r01=%.3f  **r11=%.3f**  '
              '相乘预测=%.3f  比值 r11/(r10·r01)=%.3f'
              % (rr, row['00'], r10, r01, r11, pred, r11 / pred))
if tab:
    rs = []; sp10 = []; sp01 = []; sp11 = []
    for rr, row in sorted(tab.items()):
        r10 = row['00'] / row['10']; r01 = row['00'] / row['01']; r11 = row['00'] / row['11']
        rs.append(r11 / (r10 * r01)); sp10.append(r10); sp01.append(r01); sp11.append(r11)
    med = statistics.median(rs)

    # ★★ **分辨力闸（第一版没有这一条，是我的判据缺陷 —— 留痕）**
    #   第一版直接按 `|med-1| ≤ 0.05` 判"相乘/次相乘/超相乘"。
    #   但实测各轮 r10 在 **0.880–1.095**、r01 在 **0.802–1.210** 之间跳 ——
    #   **单个开关的效应本身就淹没在噪声里** ⇒ 那个 +9.8% 是**噪声，不是结论**。
    #   ⇒ 必须先问"**本配置分辨得出这个效应吗**"，再谈相乘/次相乘。
    def spread(v):
        return (max(v) / min(v) - 1.0) if min(v) > 0 else float('inf')
    s10, s01, s11 = spread(sp10), spread(sp01), spread(sp11)
    print()
    print('  ── ★ 分辨力闸（**判据必须先过这一关**）──')
    print('     各臂比值的**逐轮离散度**：r10 %.1f%%（%.3f–%.3f）、'
          'r01 %.1f%%（%.3f–%.3f）、r11 %.1f%%（%.3f–%.3f）'
          % (100 * s10, min(sp10), max(sp10), 100 * s01, min(sp01), max(sp01),
             100 * s11, min(sp11), max(sp11)))
    print('     被检验的效应大小 ≈ **40%**（若两开关各 ~1.18× ⇒ 相乘预测 ≈ 1.40）')
    RESOLVABLE = max(s10, s01, s11) < 0.10
    print('     ⇒ 判据（离散度 < 10%% 才算分辨得出）：%s'
          % ('✅ 分辨得出' if RESOLVABLE else
             '❌ **分辨不出** —— 逐轮离散度 %.0f%% 远大于效应本身' % (100 * max(s10, s01, s11))))
    print()
    print('  ⇒ **r11 / (r10·r01) 的中位 = %.4f**   区间 [%.4f, %.4f]（%d 轮）'
          % (med, min(rs), max(rs), len(rs)))
    if not RESOLVABLE:
        print('  ⇒ **判定：⚠ 无法判定** —— 本配置（N=%s / %s 步 / %d 轮）的噪声'
              '**大于**要测的效应。' % (NCONF, STEPS, len(rs)))
        print('     记账：**不许**把这 %+.1f%% 读成"超相乘"（第一版就是这么误读的）。'
              % (100 * (med - 1)))
        print('     要判定需要：① 更多轮次（≥20）；② 或改用**分块记账**判单开关'
              '（P17）再单独看组合。')
    else:
        dev = med - 1.0
        if abs(dev) <= 0.05:
            print('  ⇒ 判据（|偏差| ≤ 0.05）：✅ **相乘成立** ⇒ 两个开关的收益**互相独立**')
        elif dev < 0:
            print('  ⇒ 判据（|偏差| ≤ 0.05）：❌ **次相乘**（偏差 %.1f%%）⇒'
                  ' 两个开关**争同一份资源** ⇒ 必须记账，**不许解释成"正常"**' % (100 * dev))
        else:
            print('  ⇒ 判据（|偏差| ≤ 0.05）：⚠ **超相乘**（偏差 +%.1f%%）⇒ 少见，要查' % (100 * dev))
PYEOF
echo "=== R581 DECOMP2x2 DONE $(date '+%F %T') ===" | tee -a "$LOG"
