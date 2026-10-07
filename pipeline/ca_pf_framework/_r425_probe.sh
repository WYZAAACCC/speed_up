#!/bin/bash
# _r425_probe.sh —— ★ **A/B 双臂的"实测预算"探针**（跑 4 步，量 s/步 与峰值内存）
#
# ## 为什么必须先探针
# `_r424` 的 13.7 h / 2.31 h 是**按 nreg 线性外推**的（13 场 5.4 s/步 ⇒ 25 场 10.4 s/步），
# **没有实测**。直接按外推启一个 13.7 小时的作业，若外推错了就白烧。
# ⇒ 先用**逐字相同**的配置跑 4 步，量准 `s/步` 与 `峰值 RSS`，再决定放不放。
#
# ## 判据
#   Q-1 配置能跑起来、无 Traceback。
#   Q-2 量到 `s/步` 与峰值 RSS（写进日志）。
#   Q-3 **播种行为核对**：不带 `--multi-block` 时 t=0 到底播了几片？
#       （`§189` 的推理是"只播第 1 片"，必须眼见为实）
#   Q-4 `nreg_used` / 场数 = 25。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

# 24 个场 = 变体 {1,3,5,7,9,11} 各 4 份（自协调集，`§178` 实测 r_min≈0.001）
LATHS="1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11"

COMMON="--N 112 --dx-nm 62.5 --steps 4 --every 1 --snap-every 4 --pair-every 2 \
--norm-smooth 0 --nthreads 3 --reinit-dt 1e-4 \
--laths $LATHS --plate-L 1000 --plate-W 500 --plate-T 510 \
--grow-stack --nuc-law athermal --nuc-init 8 --nuc-fresh-every 5 \
--alpha-km 0.041739 --T-end 298.0 --facet-proj 0 --facet-excl 0"

rm -rf _exp/_bk_mb/dry_probeAB
echo "############ 探针（4 步）  $(date '+%F %T')"
/usr/bin/time -v "$PY" -u _bk_exp.py $COMMON \
    --tag probeAB --out _exp/_bk_mb > _r425_probe.log 2> _r425_probe_time.log
echo "退出码=$?"

echo
echo "======== Q-1 异常 ========"
echo "  Traceback = $(grep -c Traceback _r425_probe.log || true)"
echo "  顶层异常  = $(grep -cE '^(ValueError|TypeError|NameError|KeyError|IndexError|RuntimeError|UnboundLocalError):' _r425_probe.log || true)"

echo
echo "======== Q-2 实测 s/步 与峰值 RSS ========"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' _r425_probe_time.log || true
"$PY" - <<'PYEOF'
import csv, os
p = '_exp/_bk_mb/dry_probeAB/series.csv'
if os.path.exists(p):
    rows = list(csv.DictReader(open(p)))
    print('  CSV 行数 = %d' % len(rows))
    ws = [float(r['wall_s']) for r in rows if r.get('wall_s') not in (None, '')]
    if ws:
        print('  逐步 wall_s = %s' % [round(x, 2) for x in ws])
        print('  ⇒ 中位 s/步 = %.2f' % float(__import__('numpy').median(ws)))
    for k in ('nreg_used', 'Vt', 'nslab_n', 'nf3', 'blk_nprof'):
        if k in rows[0]:
            print('  %-10s = %s' % (k, [r[k] for r in rows]))
PYEOF

echo
echo "======== Q-3 播种行为（不带 --multi-block 时播了几片？） ========"
grep -nE '播种|播下|片|n_seeded|只播' _r425_probe.log | head -14

echo
echo "======== Q-4 场数与形核接线 ========"
grep -nE '构造 |athermal 形核律|导出板条数|C-3|步数下界|表示上限|nreg' _r425_probe.log | head -14

echo
echo "======== 尾部 ========"
tail -8 _r425_probe.log
