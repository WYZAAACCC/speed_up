#!/bin/bash
# _r215_dbg.sh —— 查 `--diag-terms` 的打印为什么没出现。
cd "$(dirname "$0")" || exit 1
echo "=== ① run log 里 '135.7' 命中数 ==="
grep -c '135\.7' _w2_r210_saSet2_run.log || true
echo
echo "=== ② _bk_exp.py 里 diag_terms / 三项量级 出现的位置 ==="
grep -n 'diag_terms\|三项量级' _bk_exp.py | head -24
echo
echo "=== ③ argparse 的 dest 是不是 diag_terms ==="
grep -n -A2 "add_argument('--diag-terms'" _bk_exp.py
echo
echo "=== ④ 引擎里的 diag 块头 ==="
grep -n 'diag_terms_on\|self.diag_terms = None\|self.diag_terms = dict' \
  windowB_surface.py | head
echo
echo "=== ⑤ 打印条件那几行的原文 ==="
grep -n -B2 -A6 'if bool(a.diag_terms)' _bk_exp.py | head -30
