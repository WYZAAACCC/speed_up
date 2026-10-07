#!/bin/bash
# R50 正对照（P1-29 / V-1′）：
#   ① 语法 + 不崩
#   ② V-1′ 必须在**归档臂**（无 `nslab_nu` 列）上也能算 —— 靠从 `runs` 现算
#   ③ 已知的"多读"臂（`dry_mb1Ls` 3→5、`eng_eng3` 6→7）必须被点出来
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY -c "import ast;ast.parse(open('_bk_verdict.py').read())" || { echo SYNTAX-FAIL; exit 1; }
for f in _bk_exp.py; do $PY -c "import ast;ast.parse(open('$f').read())" || echo "SYNTAX-FAIL $f"; done
echo "SYNTAX OK"
echo
for spec in "_exp/_bk_mb:mb1Ls" "_exp/_bk_eng:eng3" "_exp/_bk_eng:eng12" \
            "_exp/_bk_mb:mb1L" "_exp/_bk_closed:cln11"; do
  root="${spec%%:*}"; tag="${spec##*:}"
  echo "########## $tag"
  $PY _bk_verdict.py --root "$root" --tag "$tag" --arms dry,eng 2>&1 \
    | grep -E "V-1'|V-1′" | head -2
  echo
done
