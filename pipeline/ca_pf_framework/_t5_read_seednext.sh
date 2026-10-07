#!/bin/bash
# _t5_read_seednext.sh --- ★★★★★ 逐行读 `_seed_next()`（驱动层形核；**不经 nucleate，日志无事件**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `_seed_next` 的定义位置 ════'
grep -n "_seed_next" _bk_exp.py | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ② 定义体（逐行）════'
L=$(grep -n "def _seed_next" _bk_exp.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  echo "  （_bk_exp.py 第 $L 行起）"
  sed -n "${L},$((L+85))p" _bk_exp.py | nl -ba -v"$L" | cut -c1-150
else
  echo '  ⚠ 没找到 `def _seed_next`'
fi
