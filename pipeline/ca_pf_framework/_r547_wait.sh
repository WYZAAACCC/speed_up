#!/usr/bin/env bash
# _r547_wait.sh —— 等 `_r547` 跑完，打印 ① fresh 归因 ② 回归（与归档 b4 逐位比）
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
for i in $(seq 1 40); do
  n=$(pgrep -f 'tag fr_' | wc -l)
  [ "$n" -eq 0 ] && { echo "（第 $i 次轮询：已无 fr_* 进程）"; break; }
  sleep 60
done
echo
echo "##################### ① 并行驱动汇总"
tail -12 _w2_r547_par.log
echo
for t in fr_b8ps fr_reg; do
  echo "##################### ② $t 的 fresh 归因（N14）"
  grep -o "dbg={[^}]*}" "_w2_r537_$t.log" | tail -1 | tr ',' '\n' | sed 's/^ */  /'
  echo "  ── 末态"
  grep -n '^  \[' "_w2_r537_$t.log" | tail -1 | cut -c1-180
  echo
done
echo "##################### ③ 回归：`fr_reg`（B=4、默认）vs 归档 `b4`（同配置）"
A="_exp/_bk_par/fr_reg/dry_fr_reg/series.csv"
B="_exp/_bk_par/b4/dry_b4/series.csv"
if [ -f "$A" ] && [ -f "$B" ]; then
  echo "  fr_reg: $(wc -l < "$A") 行 / b4: $(wc -l < "$B") 行"
  if diff -q "$A" "$B" > /dev/null 2>&1; then
    echo "  ⇒ ✅ **逐位相同**（默认路径回归通过）"
  else
    echo "  ⇒ ⚠ 有差异；差异行数：$(diff "$A" "$B" | grep -c '^[<>]' || true)"
    echo "  ⇒ 头 3 处差异："
    diff "$A" "$B" | head -6
  fi
else
  echo "  ⚠ 缺文件：A=$A B=$B"
fi
