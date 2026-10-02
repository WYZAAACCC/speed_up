#!/bin/bash
# _r581_alloc160.sh --- ★★★★★★★ **A4 的判决实验：N=160 上量峰值 RSS 与 s/步**
#
# ## 用户授权（2026-10-02）
# > 「按照你的建议去掉那两个阈值变量（ARENA_MAX=2 保留），**但先补一步**：
# >   **在 N=160 上量一次峰值 RSS 与 s/步，确认峰值不涨到危险区**」
#
# ## 设计（**单变量：只差 MALLOC 环境变量**）
# | 臂 | `MALLOC_MMAP_THRESHOLD_` | `MALLOC_TRIM_THRESHOLD_` | `MALLOC_ARENA_MAX` | 角色 |
# |---|---|---|---|---|
# | **TUNED** | 65536 | 65536 | 2 | **= 仓库 134 个脚本的现状** |
# | **★ ARENA** | **（不设）** | **（不设）** | **2** | **★ 用户要采用的配置** |
# | **PLAIN** | （不设） | （不设） | （不设） | 参考（"一个都不设"） |
#
# ## 工作负载
# **与 `p2_m12ov` **逐字同一条命令行**（**N=160、`nv`=240、全优化开满、含 `--ufv-c 1`**），
# 只把 `--steps` 改成 **30**（够出峰值与步速）、换 tag/out。**
#
# ## 判据（**预先写死**）
# | 观察 | 判决 |
# |---|---|
# | **ARENA 的峰值 RSS ≤ TUNED 的峰值 + 5%** | **✅ 安全 ⇒ 可以改那 134 个脚本** |
# | **ARENA 的峰值 > TUNED 的峰值 × 1.10** | **❌ 进危险区 ⇒ 不改，回来请示** |
# | **ARENA 的 s/步 ≈ TUNED 的 0.6×（即快 ~1.6×）** | **✅ 收益复现** |
# | **ARENA 与 TUNED 的 s/步差不多** | **⚠ N=160 上收益不成立 ⇒ 记账后再定** |
# | **臂不跑 / `Traceback`** | **⚠ 无法判定** |
#
# ⚠ **串行跑**（每臂 ~10–12 GB，WSL 只有 24 GB ⇒ P23：加车道看内存，不看空闲核）
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_alloc160"
LOG=_w2_r581_alloc160.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ★ 与 p2_m12ov 逐字相同，只把 --steps 30、--snap-every 30、tag/out 换掉
BASE="--N 160 --dx-nm 62.5 --steps 30 --every 5 --snap-every 30 --pair-every 50 \
 --norm-smooth 0 --phi-band-every 200 --eng-cadence 30 --nthreads 4 \
 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 \
 --reinit-band 6.0 --nuc-overlap-nm 62.5 --eps0-mode einsum --ed-pair gather \
 --k-loop act --act-mode bincount --argmin2-mode copyto --grad-mode sliced \
 --pf-phi onfly --h-chunk 4 --extend-mode near --eps0-tile 4 \
 --argmin2-reuse 1 --ufv-c 1 --bbox-mode axis"
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

say "=== R581-R184：A4 判决实验（N=160，三臂串行）==="
say "TUNED=三变量全开（现状） / ARENA=只留 ARENA_MAX=2（目标） / PLAIN=都不设（参考）"

run() {  # $1=tag  $2=档位
  local tag="$1" mode="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  local avail
  avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
  say "起 $tag（$mode）；available=${avail} MB"
  if [ "$avail" -lt 12000 ]; then
    say "  ⚠ 内存不足 12 GB ⇒ **跳过 $tag**（不许硬上，P39）"
    return 3
  fi
  local t0 t1
  t0=$(date +%s)
  case "$mode" in
    TUNED) MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 \
             /usr/bin/time -v taskset -c 0-7 $PY -u _bk_exp.py $BASE \
             --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_alloc160_${tag}.log" 2> "_w2_r581_alloc160_${tag}.time" ;;
    ARENA) MALLOC_ARENA_MAX=2 \
             /usr/bin/time -v taskset -c 0-7 $PY -u _bk_exp.py $BASE \
             --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_alloc160_${tag}.log" 2> "_w2_r581_alloc160_${tag}.time" ;;
    *)     env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
             /usr/bin/time -v taskset -c 0-7 $PY -u _bk_exp.py $BASE \
             --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_alloc160_${tag}.log" 2> "_w2_r581_alloc160_${tag}.time" ;;
  esac
  t1=$(date +%s)
  say "  $tag 结束：exit=$?，墙钟 $((t1-t0)) s，Traceback=$(grep -c '^Traceback' "_w2_r581_alloc160_${tag}.log" 2>/dev/null || echo 0)"
  sleep 5
}

run TUNED TUNED
run ARENA ARENA
run PLAIN PLAIN

say "── ★ 判决表 ──"
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import csv, os, re, sys
import numpy as np
ROOT = sys.argv[1]
ARMS = [('TUNED', '三变量全开（现状）'), ('ARENA', '只留 ARENA_MAX=2（目标）'),
        ('PLAIN', '都不设（参考）')]
print()
print('=' * 104)
print('A4 判决：N=160 / nv=240 / 全优化开满（含 --ufv-c 1）/ 30 步')
print('=' * 104)
print('  %-7s %-14s %-13s %-11s %-11s %s' %
      ('臂', '峰值 RSS(MB)', '中位 s/步', '总步数', '末步', '说明'))
print('  ' + '-' * 100)
res = {}
for tag, desc in ARMS:
    tp = '_w2_r581_alloc160_%s.time' % tag
    peak = None
    if os.path.exists(tp):
        txt = open(tp, encoding='utf-8', errors='replace').read()
        m = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)', txt)
        if m:
            peak = int(m.group(1)) / 1024.0
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    med = last = n = None
    if os.path.exists(p):
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        n = len(rows)
        if rows:
            last = rows[-1][list(rows[0].keys())[0]]
        ws = []
        for r in rows[1:]:
            try:
                ws.append(float(r.get('wall_s', '')))
            except Exception:
                pass
        if ws:
            med = float(np.median(ws))
    res[tag] = dict(peak=peak, med=med, n=n, last=last)
    print('  %-7s %-14s %-13s %-11s %-11s %s' %
          (tag, ('%.0f' % peak) if peak else '—',
           ('%.2f' % med) if med else '—', n if n else '—', last or '—', desc))
print()
t, a, pl = res.get('TUNED'), res.get('ARENA'), res.get('PLAIN')
if t and a and t['peak'] and a['peak']:
    r = a['peak'] / t['peak']
    print('  ★ **峰值**：ARENA/TUNED = %.0f / %.0f = **%.3f×**' % (a['peak'], t['peak'], r))
    if r <= 1.05:
        print('     ⇒ ✅ **安全（≤1.05×）⇒ 可以改那 134 个脚本**')
    elif r <= 1.10:
        print('     ⇒ ⚠ **边缘（1.05–1.10×）⇒ 建议带余量再改，并记账**')
    else:
        print('     ⇒ ❌ **进危险区（>1.10×）⇒ **不改**，回来请示**')
if t and a and t['med'] and a['med']:
    sp = t['med'] / a['med']
    print('  ★ **步速**：TUNED/ARENA = %.2f / %.2f = **%.3f×**（>1 ⇒ ARENA 更快）'
          % (t['med'], a['med'], sp))
    if sp >= 1.3:
        print('     ⇒ ✅ **收益在 N=160 上复现**')
    elif sp >= 1.05:
        print('     ⇒ ⚠ **收益比 N=64 小（1.64× → %.2f×）⇒ 记账**' % sp)
    else:
        print('     ⇒ ❌ **N=160 上收益不成立 ⇒ **不改**，回来请示**')
print('=' * 104)
PYEOF
say "=== R581-R184 ALLOC160 DONE ==="
