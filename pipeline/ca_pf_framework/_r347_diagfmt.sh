#!/usr/bin/env bash
# _r347_diagfmt.sh -- 看 --diag-terms 在日志里的真实格式
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
f=_w2_r280_saSet2F2P0_run.log
echo "=== 含 'diag' / '三项' / 'F2' 的行 ==="
grep -n -E 'diag|三项|F2|F1|F3' "$f" | tail -30
