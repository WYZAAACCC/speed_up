#!/bin/bash
# R50 正对照（P1-28 的修复）：
#   ① 单变异臂（cln11 / mb1s）⇒ V-1 必须**显式写明"恒真、无分辨力、不参与判决"**
#   ② 多变异臂（mb1L）      ⇒ V-1 必须**仍然判 nf3_col**（且写明有分辨力）
#   ③ 归档臂（eng12）        ⇒ 同样要命中"恒真"分支（它是历史结论的载体）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY -c "import ast;ast.parse(open('_bk_verdict.py').read())" || { echo "SYNTAX-FAIL"; exit 1; }

for spec in "_exp/_bk_closed:cln11" "_exp/_bk_mb:mb1s" "_exp/_bk_mb:mb1L" \
            "_exp/_bk_eng:eng12" "_exp/_bk_mb:mb1s62"; do
  root="${spec%%:*}"; tag="${spec##*:}"
  echo "########## $tag   (root=$root)"
  $PY _bk_verdict.py --root "$root" --tag "$tag" --arms dry,eng 2>&1 \
    | grep -E 'V-1 ' | head -2
  echo
done
