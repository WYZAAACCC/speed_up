#!/bin/bash
# _r581_engseed_check.sh --- 撤回 `--nuc-seed` 之后的复核：
#   ① `_bk_exp.py` 语法 OK；② 真正的旋钮 `--eng-seed` 存在且默认值是多少；
#   ③ 与归档快照里的 `_bk_exp.py` **逐字节相同**（证明撤回干净）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "── ① 语法 ──"
$PY -c 'import ast; ast.parse(open("_bk_exp.py").read()); print("   SYNTAX OK")'

echo "── ② 真正的种子旋钮（搜语义，不是搜拼写）──"
grep -n "eng-seed\|eng_seed" _bk_exp.py | head -8 | sed 's/^/   /'

echo "── ③ 与编辑前的快照逐字节比 ──"
SNAP=_r580_backup/beforeNucSeed_20261002_115012/_bk_exp.py
if [ -f "$SNAP" ]; then
  a=$(sha256sum _bk_exp.py | cut -c1-16)
  b=$(sha256sum "$SNAP" | cut -c1-16)
  echo "   当前   $a"
  echo "   编辑前 $b"
  if [ "$a" = "$b" ]; then
    echo "   ⇒ ✅ **逐字节相同 ⇒ 撤回干净，主副本恢复原状**"
  else
    echo "   ⇒ ❌ 不同 ⇒ 撤回不干净，必须查（不许留着半成品）"
    diff <(cat "$SNAP") _bk_exp.py | head -20 | sed 's/^/     /'
  fi
else
  echo "   ⚠ 找不到快照 $SNAP"
fi
