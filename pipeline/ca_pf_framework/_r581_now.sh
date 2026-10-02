#!/bin/bash
# _r581_now.sh --- 一行看全部状态（臂 / 步数 / 内存 / 守卫 / 队列）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== $(date '+%F %T') ==="
bash _r581_ps.sh 2>/dev/null | tail -5
echo "--- 进度 ---"
for t in p2_b5 p2_b3 p2_b5ov p2_b5ps; do
  f="_exp/_bk_p2/dry_${t}/series.csv"
  if [ -f "$f" ]; then
    n=$(wc -l < "$f")
    last=$($PY -c "
import numpy as np,sys
try:
    a=np.genfromtxt('$f',delimiter=',',names=True)
    import numpy as np
    st=np.atleast_1d(a['step'])[-1]; vt=np.atleast_1d(a['Vt'])[-1]
    ns=np.atleast_1d(a['nslab_n'])[-1]; nf=np.atleast_1d(a['nf3_col'])[-1]
    print('step=%-5d Vt=%.4f um3  nslab=%d nf3col=%d' % (st, vt*1e18, ns, nf))
except Exception as e: print('（读不了: %r）' % (e,))
" 2>/dev/null)
    printf '  %-9s 行=%-6s %s\n' "$t" "$n" "$last"
  else
    printf '  %-9s （还没有 series.csv）\n' "$t"
  fi
done
echo "--- 守卫 / 队列 ---"
for f in _w2_r581_softguard.log _w2_r581_memguard.log _w2_r581_p2q.log; do
  printf '  %-26s %s\n' "$f" "$(tail -1 "$f" 2>/dev/null | cut -c1-100)"
done
echo "--- 在跑的守卫进程 ---"
# ⚠ 第一版用 `pgrep -af 'softguard|memguard'` —— **它报了"无"，而两个守卫其实都活着**
#   （`ps` 实测：softguard pid 7941、memguard pid 338）。
#   ⇒ 按 P6「量具错了和被测量对象错了长得一模一样」，改成 `ps | grep`（更直白），
#     并且**同时打印计数**，避免"空输出"被误读成"没有"。
for pat in softguard memguard; do
  n=$(ps -eo args --no-headers 2>/dev/null | grep "$pat" | grep -v grep | wc -l)
  printf '  %-10s 进程数=%s  %s\n' "$pat" "$n" \
    "$(ps -eo pid,etime,args --no-headers 2>/dev/null | grep "$pat" | grep -v grep | awk '{printf "pid=%s 已跑=%s ",$1,$2}')"
done
