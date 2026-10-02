#!/bin/bash
# _r581_prof.sh --- 在**生产意图档**下打一次全量分块记账，作为 L2–L6 的靶子表。
#
# ⚠ 口径：`_r576_prof.py` 的算例是它**自己的**测试态（`_r561_opfacct.build()`），
#   与 `_bk_exp.py` 的真实算例**不同**。所以读数只用来**排序与定位**，
#   不作为"某算子占生产步 X%"的最终结论（那个要用真实路径的 A/B）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
export R576_N="${R581PROF_N:-64}" R576_NV="${R581PROF_NV:-24}"
export R576_STEPS="${R581PROF_STEPS:-8}" R576_WORKERS="${R581PROF_WORKERS:-4}"
export R576_TAG="${R581PROF_TAG:-PROD}"
export R576_OUT="${R581PROF_OUT:-_w2_r581_prod.log}"
# 生产意图档：7 个已验证开关 + extend=near（**全部逐位相同**）
export R561_EPS0=einsum R561_EDPAIR=gather R561_KLOOP=act R561_ACT=bincount \
       R561_ARG2=copyto R581_EXTEND=near
# ★ 生产用 `--pf-phi onfly` ⇒ `fe.ed.soft_phi` + `el.e0.einsum` 被 `el.e0.stream`
#   取代。不设这一项，记账表会指向**错靶子**（R581 实测：两者构成完全不同）。
export R561_PFPHI="${R581PROF_PFPHI:-onfly}"
export R561_GRAD="${R581PROF_GRAD:-sliced}"
$PY _r576_prof.py > "_w2_r581_prod_stdout.log" 2>&1
echo "exit=$?"
sed -n '/互斥顶层块/,/顶层合计/p' "$R576_OUT"
echo "--- 关键子块 ---"
sed -n '/关键子块/,/GAP/p' "$R576_OUT"
echo "--- 判据 ---"
grep -E '^  P0=|覆盖率|干净单步' "$R576_OUT"
