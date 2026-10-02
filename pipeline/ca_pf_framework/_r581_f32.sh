#!/bin/bash
# _r581_f32.sh --- ★★★★★★★ **C5 的唯一拦路条件**：`--phi-prec f32` 会不会**改 argmin 次序**？
#
# ## 为什么这是判决实验
# R168 的内存账：`nv`=540 时
#   * **f64 ⇒ 23.04 GB ⇒ 超 22 GB 预算 ❌**
#   * **f32 ⇒ 14.17 GB ⇒ 进 ✅**
# ⇒ **C5 要用 `nv`=540 就**必须** f32**。而 goal §(18) 判据⑫ **逐字**要求：
#   「`proj2` 语义、**`argmin` 次序**、`edge_order=2` 边界公式**都不得改**」
# ⇒ ⇒ **所以问题的**准确形式**是：**f32 会不会改变 `argmin` 的结果（`region` 数组）？****
#
# ## 实验（**单变量：只差 `--phi-prec`**）
# | 臂 | `--phi-prec` | 其余**逐字相同** |
# |---|---|---|
# | **P64** | **f64（默认）** | ✅ |
# | **P32** | **f32** | ✅ |
#
# ## 判据（**预先写死**）
# | 观察 | 判决 |
# |---|---|
# | **`region` **逐位相同** 且 `series.csv` 的物理列**逐位相同**** | **✅ f32 安全 ⇒ C5 可用 f32 ⇒ `nv`=540 可行** |
# | **`region` **逐位相同**，但物理列有**小差**（给出 `max|Δ|/max`）** | **⚠ 可用，但**必须显式标注容差**（goal 判据③ 允许"明确标注容差"） |
# | **★ `region` **不同**** | **❌ f32 改了 `argmin` 次序 ⇒ **判为降精度，违反判据⑫** ⇒ C5 **必须用 f64** ⇒ `nv` 上限降到 ~500** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_f32"
STEPS=30
LOG=_w2_r581_f32.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every $STEPS \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"
m=4
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")

say "=== R581-R169：f32 vs f64（只差 --phi-prec）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB"
[ "$avail" -lt 1500 ] && { say "❌ 内存不足"; exit 3; }

run() {  # $1=tag $2=prec
  local tag="$1" prec="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  say "起 $tag（--phi-prec $prec）"
  taskset -c 12-15 $PY -u _bk_exp.py $BASE --phi-prec "$prec" \
    --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_f32_${tag}.log" 2>&1
  say "  $tag exit=$? Traceback=$(grep -c '^Traceback' "_w2_r581_f32_${tag}.log" || true)"
}
run P64 f64
run P32 f32

say "── ★ 判决表 ──"
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import csv, os, sys
import numpy as np
ROOT = sys.argv[1]
print()
print('=' * 94)
print('f32 vs f64：① `region` 是否逐位相同  ② series.csv 的物理列差多少')
print('=' * 94)

# ① region（★ 这是 goal 判据⑫ 的 `argmin` 次序）
def snaps(tag):
    d = os.path.join(ROOT, 'dry_' + tag)
    if not os.path.isdir(d):
        return None
    f = sorted([x for x in os.listdir(d) if x.startswith('snap_')],
               key=lambda x: int(x.split('_')[1].split('.')[0]))
    if not f:
        return None
    z = np.load(os.path.join(d, f[-1]))
    return {k: z[k] for k in z.files} if 'region' in z.files else None

s64, s32 = snaps('P64'), snaps('P32')
if s64 is None or s32 is None:
    print('  ⚠ 缺快照 ⇒ 无法比 `region`')
else:
    print('  ── ① 快照对比（末一个快照）──')
    for k in ('region', 'vmap_keys', 'vmap_vals', 'phi', 'laths'):
        if k not in s64 or k not in s32:
            continue
        a, b = np.asarray(s64[k]), np.asarray(s32[k])
        same = (a.shape == b.shape) and bool(np.array_equal(a, b))
        extra = ''
        if not same and a.dtype.kind == 'f' and a.shape == b.shape:
            m = max(np.nanmax(np.abs(a)), 1e-300)
            extra = '  最大相对差=%.3e  不同元素=%d/%d' % (
                np.nanmax(np.abs(a - b)) / m,
                int(np.sum(a != b)), a.size)
        star = '★ **这是 argmin 的结果**' if k == 'region' else ''
        print('     %-12s %s %s %s' % (k, '✅ 逐位相同' if same else '★ 不同', extra, star))

# ② series.csv
def rows(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    return list(csv.DictReader(open(p, encoding='utf-8', errors='replace'))) \
        if os.path.exists(p) else None
r64, r32 = rows('P64'), rows('P32')
print()
if r64 is None or r32 is None:
    print('  ⚠ 缺 series.csv')
else:
    hdr = list(r64[0].keys())
    diff, mx = {}, {}
    for x, y in zip(r64, r32):
        for k in hdr:
            va, vb = x.get(k, ''), y.get(k, '')
            try:
                fa, fb = float(va), float(vb)
                if fa != fb and not (fa != fa and fb != fb):   # ★ NaN 感知（P16）
                    diff[k] = diff.get(k, 0) + 1
                    mx[k] = max(mx.get(k, 0.0),
                                abs(fa - fb) / max(abs(fa), abs(fb), 1e-300))
            except Exception:
                if va != vb:
                    diff[k] = diff.get(k, 0) + 1
    phys = {k: n for k, n in diff.items() if k not in ('wall_s', 't_wall', 'elapsed')}
    print('  ── ② series.csv：%d 列，**物理列不同 %d 个**（NaN 感知后）──' % (len(hdr), len(phys)))
    if not phys:
        print('     ✅ **物理列全逐位相同**')
    else:
        for k in sorted(phys, key=lambda z: -mx.get(z, 0))[:10]:
            print('     %-18s %d 行  最大相对差=%.3e' % (k, phys[k], mx.get(k, 0)))
print()
print('  ★ 判读：')
print('   · **`region` 逐位相同 + 物理列逐位相同** ⇒ ✅ f32 安全 ⇒ C5 可用 f32（`nv`=540 可行）')
print('   · **`region` 逐位相同、物理列有小差** ⇒ ⚠ 可用但**必须显式标注容差**')
print('   · **`region` 不同** ⇒ ❌ **f32 改了 argmin 次序** ⇒ 判为降精度 ⇒ C5 必须 f64（`nv` 上限 ~500）')
print('=' * 94)
PYEOF
say "=== R581-R169 F32 DONE ==="
