#!/bin/bash
# _r581_det.sh --- ★★★★★★ **跨进程确定性测试**（R161 的发现引出的**判决实验**）
#
# ## 为什么必须做
# R161 实测：**F 与 L 参数逐字相同、`seeds.npz`**逐位相同**、**step 0 读数逐位相同**，
# 但 **step 5 就分叉**（`nf2`：0 vs 477）。
# 而 `windowB_surface.py:1542` 的 `seed` 默认 **11**（**确定**）⇒ 理论上应当一致。
# **⇒ 唯一的嫌疑是**跨进程不确定性**** —— 最经典的来源是 **Python 的哈希随机化**
# （`PYTHONHASHSEED` 每个进程不同 ⇒ `set`/`dict` 迭代序不同 ⇒ 若它泄进任何求和，结果就变）。
#
# ## 实验（**三臂，单变量**）
# | 臂 | 设置 | 预期 |
# |---|---|---|
# | **D1** | 同参数、**不设** `PYTHONHASHSEED` | 与 D2 比 |
# | **D2** | 同参数、**不设** `PYTHONHASHSEED` | **★ 若 D1≠D2 ⇒ 跨进程不确定（哈希随机化）** |
# | **D3** | 同参数、**`PYTHONHASHSEED=0`** | **★ 若 D1≠D2 而 D1==D3 ⇒ 元凶就是哈希随机化** |
#
# ## 判据（**预先写死**）
# * **D1 == D2** ⇒ 引擎跨进程**确定** ⇒ F/L 的分叉另有原因（继续查）；
# * **D1 ≠ D2 且 D1 == D3** ⇒ **★ 确认哈希随机化** ⇒ **必须** `PYTHONHASHSEED=0`**才能跨进程比较**；
# * **D1 ≠ D2 且 D1 ≠ D3** ⇒ 还有**别的**非确定源（如线程归约序）⇒ 继续查。
#
# ## 规模（**小而快**）
# **N=64、`m`=4（`nv`=48）、30 步** ⇒ 每臂 ~1–2 min、~1 GB。
# **⚠ 串行跑**（内存紧张；P23/P39）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_det"
STEPS=30
LOG=_w2_r581_det.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 30 \
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

say "=== R581-R161：跨进程确定性测试（3 臂 × $STEPS 步，串行）==="
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：available=${avail} MB"
[ "$avail" -lt 1200 ] && { say "❌ 内存不足 ⇒ 退出"; exit 3; }

run_one() {  # $1=tag  $2=HASHSEED(空=不设)
  local tag="$1" hs="${2:-}"
  if [ -d "$ROOT/dry_$tag" ]; then
    mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  fi
  say "起 $tag（PYTHONHASHSEED=${hs:-未设}）"
  if [ -n "$hs" ]; then
    PYTHONHASHSEED="$hs" taskset -c 12-15 $PY -u _bk_exp.py $BASE \
      --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_det_${tag}.log" 2>&1
  else
    taskset -c 12-15 $PY -u _bk_exp.py $BASE \
      --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_det_${tag}.log" 2>&1
  fi
  say "  $tag 结束 exit=$?；Traceback=$(grep -c '^Traceback' "_w2_r581_det_${tag}.log" || true)"
}

run_one D1 ""
run_one D2 ""
run_one D3 0

say "── ★ 判决表（逐行比 series.csv）──"
$PY - "$ROOT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import csv, os, sys
ROOT = sys.argv[1]
rows = {}
for t in ('D1', 'D2', 'D3'):
    p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        print('  %s: 无 series.csv' % t); continue
    rows[t] = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
print()
print('=' * 92)
print('跨进程确定性：D1/D2 都不设 PYTHONHASHSEED，D3 设 0')
print('=' * 92)
def cmp(a, b):
    if a not in rows or b not in rows:
        return '（缺数据）'
    ra, rb = rows[a], rows[b]
    if len(ra) != len(rb):
        return '★ 行数不同（%d vs %d）' % (len(ra), len(rb))
    hdr = [k for k in ra[0].keys()]
    ndiff = 0; first = None
    for i, (x, y) in enumerate(zip(ra, rb)):
        for k in hdr:
            try:
                if float(x[k]) != float(y[k]):
                    ndiff += 1
                    if first is None:
                        first = 'step %s 的 %s：%s vs %s' % (x[hdr[0]], k, x[k], y[k])
                    break
            except Exception:
                if x[k] != y[k]:
                    ndiff += 1
                    if first is None:
                        first = 'step %s 的 %s（字符串）' % (x[hdr[0]], k)
                    break
    return ('✅ 逐行逐列相同' if ndiff == 0
            else '★ 有 %d 行不同；首处：%s' % (ndiff, first))
print('  D1 vs D2（同设置、不同进程）: %s' % cmp('D1', 'D2'))
print('  D1 vs D3（D3 固定 hashseed=0）: %s' % cmp('D1', 'D3'))
print('  D2 vs D3                      : %s' % cmp('D2', 'D3'))
print()
print('  ★ 判读：')
print('   · **D1==D2** ⇒ 跨进程**确定** ⇒ F/L 的分叉另有原因')
print('   · **D1≠D2 且 D1==D3** ⇒ **★ 确认哈希随机化** ⇒ 跨进程比较**必须**固定 PYTHONHASHSEED')
print('   · **D1≠D2 且 D1≠D3** ⇒ 还有别的非确定源（线程归约序等）')
print('=' * 92)
PYEOF
say "=== R581-R161 DET DONE ==="
