#!/bin/bash
# _r289_r280prog.sh —— 查 `_r280` 两臂（**P0 决定性实验**）的真实进度。
cd "$(dirname "$0")" || exit 1
echo "=== _r280 两臂的日志步号 / mtime / Traceback ==="
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log; do
  if [ -f "$f" ]; then
    last=$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')
    mt=$(stat -c %y "$f" | cut -d. -f1)
    printf '  %-34s 最新步=%-6s mtime=%s Traceback=%s\n' "$f" \
      "${last:-?}" "$mt" "$(grep -c Traceback "$f" || true)"
  else
    printf '  %-34s (不存在)\n' "$f"
  fi
done
echo
echo "=== 当前时间 ==="; date '+%F %T'
echo
echo "=== 两臂的步时（最近 3 个）==="
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log; do
  [ -f "$f" ] && printf '  %-34s %s\n' "$f" \
    "$(grep -o '[0-9.]*s/步' "$f" | tail -3 | tr '\n' ' ')"
done
echo
echo "=== 两臂的关键前期输出（块内自检 / t=0 / diag）==="
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log; do
  echo "  --- $f ---"
  grep -E '块内界面自检|cov_norm|三项量级|接触面|nslab' "$f" 2>/dev/null | head -5 | sed 's/^/    /'
done
echo
echo "=== 进程 CPU 采样（20 s）==="
snap() { ps -eo pid,etime,times,pcpu,args --no-headers 2>/dev/null \
         | grep '_bk_exp[.]py' | grep -v grep \
         | sed 's/.*--tag \([A-Za-z0-9_]*\).*/\1/' | sort | tr '\n' ' '; echo; }
snap
sleep 20
snap
