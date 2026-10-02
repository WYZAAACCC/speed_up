#!/bin/bash
# _r581_d2.sh --- ★★★★★ 补做 **D1 vs D2**（把"跨进程确定"从【部分】升为**完整**）+ P42 检查
#
# ## 为什么只跑一次
# R161 已经跑过 **D1**（**不设** `PYTHONHASHSEED`）与 **D3**（设 0）：
#   * **D1 vs D3**：**只有 `wall_s` 那一列不同** ⇒ **物理量逐位相同** ⇒ 引擎**跨进程确定**（**部分证据**）；
#   * **D2 被看门狗杀了** ⇒ **"两次都不设 hashseed"那一对**没做成**** ⇒ **本轮补上**。
# **⇒ 只需再跑一条与 D1 **配置完全相同**的臂（D2），比 D1 vs D2 即可。**
#
# ## 判据（预先写死）
# | 结果 | 判定 |
# |---|---|
# | **D1 vs D2：**只有 `wall_s` 不同**（其余逐位相同）** | **✅ 跨进程确定（完整）** |
# | **D1 vs D2：**有物理列不同**** | **★ 有别的非确定源**（线程归约序等）⇒ 必须查 |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_det"
STEPS=30
LOG=_w2_r581_d2.log
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

say "=== R581-R163：补做 D2（不设 PYTHONHASHSEED，与 D1 同配置）==="
say "D1 在不在：$([ -f "$ROOT/dry_D1/series.csv" ] && echo 在 || echo '❌ 不在')"
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存：available=${avail} MB"
[ "$avail" -lt 1200 ] && { say "❌ 内存不足"; exit 3; }

if [ -d "$ROOT/dry_D2" ]; then
  mv "$ROOT/dry_D2" "$ROOT/dry_D2_superseded_$(date '+%Y%m%d_%H%M%S')"
  say "旧的 dry_D2 已 mv 归档"
fi
say "起 D2（cores 12-15）"
taskset -c 12-15 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag D2 --laths "$laths" \
  > _w2_r581_det_D2.log 2>&1
say "D2 结束 exit=$?；Traceback=$(grep -c '^Traceback' _w2_r581_det_D2.log || true)"

say "── ★ 判决表 ──"
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
print('跨进程确定性：D1/D2 **都不设** PYTHONHASHSEED；D3 设 0')
print('=' * 92)
def cmp(a, b, ignore=('wall_s',)):
    if a not in rows or b not in rows:
        return '（缺数据）', []
    ra, rb = rows[a], rows[b]
    if len(ra) != len(rb):
        return '★ 行数不同（%d vs %d）' % (len(ra), len(rb)), []
    hdr = [k for k in ra[0].keys()]
    bad = {}
    for x, y in zip(ra, rb):
        for k in hdr:
            try:
                same = (float(x[k]) == float(y[k]))
            except Exception:
                same = (x[k] == y[k])
            if not same:
                bad.setdefault(k, 0)
                bad[k] += 1
    return ('✅ 逐行逐列相同' if not bad else '★ 有差异'), bad
for a, b in (('D1', 'D2'), ('D1', 'D3'), ('D2', 'D3')):
    s, bad = cmp(a, b)
    print('  %s vs %s: %s' % (a, b, s))
    if bad:
        for k, n in sorted(bad.items()):
            tag = '（计时列，物理无关）' if k in ('wall_s', 't_wall', 'elapsed') else '★ **物理列**'
            print('       %-16s 有 %d 行不同 %s' % (k, n, tag))
    print()
print('  ★ 判读：')
print('   · **D1 vs D2 只有 `wall_s` 不同** ⇒ **✅ 跨进程确定（完整证据）**')
print('   · **D1 vs D2 有物理列不同** ⇒ ★ 有别的非确定源 ⇒ 必须查（线程归约序等）')
print('=' * 92)
PYEOF
say "=== R581-R163 D2 DONE ==="
