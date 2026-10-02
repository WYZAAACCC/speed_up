#!/bin/bash
# _r581_nt1.sh --- ★★★★★★ **判决实验：非确定性的元凶是不是线程？**
#
# ## 背景（R163）
# **D1 vs D2**（同参数、不同进程、**都不设** hashseed）在**物理列**上不同（`psi_mean` 全 7 行）⇒
# **引擎跨进程不确定**。各臂都用 **`--nthreads 2`** ⇒ 最可能是**并行归约次序**（浮点求和序变）。
#
# ## 实验（**单变量**）
# | 臂 | 设置 | 与谁比 |
# |---|---|---|
# | **S1** | **`--nthreads 1`**、30 步、`m`=4 | 与 S2 比 |
# | **S2** | **同 S1** | **★ 若 S1==S2 ⇒ **元凶是线程**** |
# | **S4** | **`--nthreads 4`** | **★ 与 S1 比 ⇒ 看线程数是否**放大**差异** |
#
# ## 判据（**预先写死**）
# * **S1 == S2（逐位，除 `wall_s`）** ⇒ **★ 单线程确定** ⇒ **元凶 = 并行归约** ⇒
#   **跨臂逐位比较必须 `--nthreads 1`**（**或改用同进程 A/B**）；
# * **S1 ≠ S2** ⇒ **还有别的非确定源**（如时间相关启发式/未固定的 `rng`）⇒ 继续查；
# * **S4 与 S1 的差异 ≥ D1 与 D2 的差异** ⇒ 支持"线程放大"。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_det"
STEPS=30
LOG=_w2_r581_nt1.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

mkbase() {  # $1 = nthreads
cat <<EOF
--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 30 \
  --pair-every 0 --norm-smooth 0 --nthreads $1 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1
EOF
}
m=4
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")

say "=== R581-R163：线程 vs 非确定性 ==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB"
[ "$avail" -lt 1200 ] && { say "❌ 内存不足"; exit 3; }

run() {  # $1=tag $2=nthreads
  local tag="$1" nt="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  say "起 $tag（--nthreads $nt）"
  taskset -c 12-15 $PY -u _bk_exp.py $(mkbase "$nt") \
    --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_nt1_${tag}.log" 2>&1
  say "  $tag exit=$? Traceback=$(grep -c '^Traceback' "_w2_r581_nt1_${tag}.log" || true)"
}
run S1 1
run S2 1
run S4 4

say "── ★ 判决表（**逐列统计**，不 break）──"
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import csv, os, sys
ROOT = sys.argv[1]
rows = {}
for t in ('S1', 'S2', 'S4', 'D1', 'D2'):
    p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
    if os.path.exists(p):
        rows[t] = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
print()
print('=' * 92)
print('线程 vs 跨进程非确定性（S1/S2: --nthreads 1；S4: --nthreads 4）')
print('=' * 92)
def stat(a, b):
    if a not in rows or b not in rows:
        return None
    ra, rb = rows[a], rows[b]
    hdr = list(ra[0].keys())
    bad = {}
    mx = 0.0
    for x, y in zip(ra, rb):
        for k in hdr:
            va, vb = x.get(k, ''), y.get(k, '')
            try:
                fa, fb = float(va), float(vb)
                if fa != fb:
                    bad[k] = bad.get(k, 0) + 1
                    d = abs(fa - fb) / max(abs(fa), abs(fb), 1e-300)
                    mx = max(mx, d)
            except Exception:
                if va != vb:
                    bad[k] = bad.get(k, 0) + 1
    return bad, mx
for a, b, label in (('S1', 'S2', '★ 同设置、都 1 线程'),
                    ('S1', 'S4', '1 线程 vs 4 线程'),
                    ('D1', 'D2', '★ 同设置、都 2 线程（R163 的发现）')):
    r = stat(a, b)
    if r is None:
        print('  %s vs %s：（缺数据）' % (a, b)); continue
    bad, mx = r
    phys = {k: n for k, n in bad.items() if k != 'wall_s'}
    print('  %-28s %s vs %s：' % (label, a, b))
    if not phys:
        print('      ✅ **物理列全逐位相同**（只有 wall_s 之类计时列不同）')
    else:
        print('      ★ 物理列不同的有 %d 个；最大相对差 = %.3e' % (len(phys), mx))
        for k, n in sorted(phys.items())[:6]:
            print('         %-16s %d 行' % (k, n))
print()
print('  ★ 判读：')
print('   · **S1==S2（只有 wall_s 不同）** ⇒ **★ 单线程确定 ⇒ 元凶 = 并行归约**')
print('   · **S1≠S2** ⇒ 还有别的非确定源')
print('=' * 92)
PYEOF
say "=== R581-R163 NT1 DONE ==="
