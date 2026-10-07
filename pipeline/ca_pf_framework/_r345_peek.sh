#!/usr/bin/env bash
# _r345_peek.sh -- 看 200 步臂日志的格式（先看原始文本再写正则）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
f=_w2_r322_near200_run.log
echo "=== emit 命令行 ==="
cat _w2_r322_emit.log | head -6
echo
echo "=== $f 前 40 行 ==="
sed -n '1,40p' "$f"
echo
echo "=== 含 ed / 变体 / cov / nf2 的行（末尾 25 条）==="
grep -n -E 'ed|变体|cov|nf2|blk' "$f" | tail -25
