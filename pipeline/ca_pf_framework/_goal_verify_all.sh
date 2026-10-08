#!/usr/bin/env bash
# _goal_verify_all.sh —— 方案的**全量验证入口**（只读，不改任何主代码）。
#
# 目录约定：
#   * 本脚本与 `_auditR712_*.py` 在 `ca_pf_framework/`（**正式验证工具**）
#   * 探究过程的脚本（含我留痕的错版）在 `ca_pf_framework/_r712_work/`
#
# 用法： cd /mnt/f/speed_up/pipeline/ca_pf_framework && bash _goal_verify_all.sh
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
W="$HERE/_r712_work"
PY=/root/miniconda3/envs/ml/bin/python
export OMP_NUM_THREADS=1
export MALLOC_MMAP_THRESHOLD_=65536
export MALLOC_TRIM_THRESHOLD_=65536
export MALLOC_ARENA_MAX=2

# ≤4 核 + nice（遵守 R630 的 CPU 纪律）
run() { nice -n 10 taskset -c 0-3 "$PY" -u "$@" 2>&1; }

echo "=============================================================="
echo " 1) 引用复验（两份终版文档里的 file:line）"
echo "=============================================================="
run "$HERE/_auditR712_final_check.py" | tail -6

echo
echo "=============================================================="
echo " 2) 公式验证（方案里新增的每条方程）"
echo "=============================================================="
run "$HERE/_auditR712_verify.py" | tail -4

echo
echo "=============================================================="
echo " 3) R712 引用的代码事实"
echo "=============================================================="
run "$HERE/_auditR712_check.py" | grep -E '^(C1|C )' | head -6

echo
echo "=============================================================="
echo " 4) facet_proj 与棱上 κ 的实测"
echo "=============================================================="
run "$W/_auditR708_facetproj.py" | grep -E 'M1|M2|M3 |N=|max\|' | head -10

echo
echo "=============================================================="
echo " 5) 量纲/单位自检（12 项）"
echo "=============================================================="
run "$W/_goal_unit_guard.py" | tail -4

echo
echo "=============================================================="
echo " 6) C 定案：M_s 的结算"
echo "=============================================================="
run "$W/_goal_C_settle.py" | grep -E 'Assuming|自洽|a 变动|低估|不确定度' | head -8

echo
echo "=============================================================="
echo " 7) A 定案：生长判据（用文献实测 Q_G）"
echo "=============================================================="
run "$W/_goal_growth_TRUE3.py" | head -34

echo
echo "=============================================================="
echo " 8) A 定案：全库 217 篇的检索命中数"
echo "=============================================================="
run "$W/_goal_A_search.py" | grep -E '命中' | head -8

echo
echo "=============================================================="
echo " 9) S1 的三段验收（**执行 S1 时**才跑；此处只声明判据）"
echo "=============================================================="
cat <<'SPEC'
  判据（先登记，可 FAIL）：
    V1 默认档（不设 CFL_GUARD）跑通，且**不产出** cfl_guard_*.txt      ⇒ 零副作用
    V2 `CFL_GUARD=warn` 与默认档的 `series.csv` **逐位相同**           ⇒ 守卫不动物理
    V3 `CFL_GUARD=warn` 产出 cfl_guard_*.txt 且出现唯一告警串          ⇒ 门控真的打开
    V4 `CFL_GUARD=abort`（CFL_GUARD_MAX 取小值）**非零退出**           ⇒ abort 档有效
    V5 打印实测的 `cfl_used` 峰值（F8 从 [推理] 升级为 [实测] 的关键数）
  实现要点（写死）：
    · 门控用**环境变量** `CFL_GUARD`（off|warn|abort，默认 off）
      —— 与仓里既有的 `SEED_CLEAN_EVERY`（`_bk_exp.py:2654`）同一套做法，
        且**不改 `_bk_exp.py` 的参数集** ⇒ 不产生 argv diff。
    · 口径 `cfl_used = dt·MOB·dG_max/dx`（与 `series.csv` 同名列 `:3589` **同一口径**）。
    · 记账落 `cfl_guard_<tag>.txt`（守卫自己写；**不能写 `meta.json`**，
      因为那份在运行开始时已 dump，见 `:2263`）；落盘失败不得影响仿真。
    · 本段**只读+只打印+可选退出**，不修改任何数值状态。
SPEC
echo
echo "全部脚本已跑完（只读；未改任何主代码）。"
