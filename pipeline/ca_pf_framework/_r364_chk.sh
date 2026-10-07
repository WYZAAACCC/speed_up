#!/usr/bin/env bash
# _r364_chk.sh -- permB1 进度 + 回归结果核对
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
D=_exp/_bk_mb/dry_permB1_200
echo "=== permB1 快照 ==="
ls "$D"/snap_*.npz 2>/dev/null | tail -3
echo "快照数: $(ls "$D"/snap_*.npz 2>/dev/null | wc -l)"
echo "=== 日志尾部 ==="
tail -4 _w2_r361_run.log 2>&1
echo "=== 进程 ==="
echo "_bk_exp 进程数: $(pgrep -c -f '_bk_exp[.]py' || echo 0)"
echo "=== 回归 ==="
grep -E '差异字段数|共有列逐位一致|FAIL = ' _w2_r362_regress.log | head -5
free -g | head -2
