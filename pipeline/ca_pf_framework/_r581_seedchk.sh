#!/bin/bash
# _r581_seedchk.sh --- 复核 `--eng-seed` 到底存不存在（P28：别假设拼写）
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_seedchk.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① `_bk_exp.py` 里所有 seed 相关的 add_argument / 赋值'
  grep -n "seed" _bk_exp.py 2>/dev/null | grep -E "add_argument|awargs|getattr\(a" | head -20
  echo
  echo '## ② `_bk_exp.py` 里 `eng_seed` 的全部出现'
  grep -n "eng_seed" _bk_exp.py 2>/dev/null | head -10
  echo
  echo '## ③ `windowB_surface.py` 里 `seed` 的构造点（签名 + 用在哪）'
  grep -n "seed" windowB_surface.py 2>/dev/null | grep -E "def |rng|default_rng|RandomState" | head -20
  echo
  echo '## ④ 引擎构造里 rng 是怎么来的（关键：谁喂 seed）'
  grep -n "rng" windowB_surface.py 2>/dev/null | head -20
} > "$OUT" 2>&1
cat "$OUT"
