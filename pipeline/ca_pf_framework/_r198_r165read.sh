#!/bin/bash
# _r198_r165read.sh —— R165 收尾：① 查错误 ② 读末态关键列 ③ 跑预登记判决 ④ 跑惰性对比。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "############ ① 错误检查（硬要求：Traceback 必须为 0）############"
for f in _w2_r165_run.log _w2_r165_saSet2F2.log _w2_r165_saOddGF2.log \
         _w2_r179.log; do
  if [ -f "$f" ]; then
    n=$(grep -c 'Traceback' "$f" || true)
    e=$(grep -cE '^(Error|Exception|[A-Za-z]*Error):' "$f" || true)
    printf '  %-28s Traceback=%s  顶层异常=%s  行数=%s\n' \
      "$f" "${n:-0}" "${e:-0}" "$(wc -l < "$f")"
  else
    printf '  %-28s (不存在)\n' "$f"
  fi
done
echo
echo "  --- 若有 Traceback，打印上下文 ---"
for f in _w2_r165_saSet2F2.log _w2_r165_saOddGF2.log _w2_r179.log; do
  [ -f "$f" ] || continue
  if grep -q 'Traceback' "$f"; then
    echo "  == $f =="
    grep -A6 'Traceback' "$f" | head -20
  fi
done

echo
echo "############ ② 惰性复现：全 120 步逐位对比 ############"
"$PY" -u _r184_inert_cmp.py 2>&1 | tail -14

echo
echo "############ ③ 预登记判决 G-1..G-4（`_r171`）############"
"$PY" -u _r171_f2verdict.py 2>&1 | tail -60
