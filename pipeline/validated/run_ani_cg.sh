#!/bin/bash
# =============================================================================
# `A_ani` 敏感性扫描（用**专门为竞争生长设计的** `test_cg.i`）
# =============================================================================
# ## 为什么用 `test_cg.i` 而不是生产输入
#
# 本轮实测：生产输入上做这个实验**不可行**，两个原因都是硬的：
#
#   ① **走不到选择发生的时刻**。生产 54×19 上 343 s 只推进到 t = 4e-6 s，
#      而凝固要 ~1e-4 s ⇒ **每档约 1 小时**，还不含每个 A 值各自的 JIT（~5 min）。
#   ② **两个便宜的观测量都无效**：
#      * `align_mean`（全域）被未熔化的基体（~92% 体积）稀释 ⇒ 实测恒为 0.4998
#      * `align_melt`（block 1 = 初始熔池）被液相拖低 —— 液相里 Ση²≈0，
#        `align4 = 0/(0+0.001) = 0` ⇒ 实测只有 0.15
#
# `test_cg.i` 是 40×40/2 序参量、**专为这个问题写的**：`L = L2a(T)·(1+A·(2·align4−1))`，
# 两个晶粒的迁移率之比就是 `(1+A)/(1−A)`；判据 `gr0_total = ∫gr0 dV` 是
# 「对齐的那个晶粒占了多少面积」。`end_time = 6e-4` 已经是设计好的时长。
#
# ⚠ 必须声明的限制：`test_cg.i` 里的 `align4 = gr0²/(gr0²+gr1²+1e-3)`
#   是**两序参量的简化版**，不是生产里那个带 `gdir_p/gdir_q` 的八序参量式。
#   所以它测的是「**A_ani 这个参数本身有没有在起作用、多大才饱和**」，
#   不是生产的定量织构。
#
# 用法： ANI_LIST="0 0.005 0.02 0.05 0.2 0.7" bash run_ani_cg.sh
# =============================================================================
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/anicg}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
ANI_LIST="${ANI_LIST:-0 0.005 0.02 0.05 0.2 0.7}"
END="${END:-6e-4}"
TMO="${TMO:-600}"
SEED="${SEED:-/root/work/jitcache_seed}"

SRC="$REPO/test_cg.i"
[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

# ⚠ 必须激活 conda 环境 —— 否则 `mpicxx` 找不到，`ParsedMaterial` 的 LLVM JIT
#   全部失败（报 `JITCompile() failed`）。AGENTS.md §3.2 教训 9，本轮又踩一次。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

for A in $ANI_LIST; do
  D="$ROOT/a$A"; mkdir -p "$D"; cd "$D"
  cp "$SRC" case.i
  # 只把 L 表达式里的那个 0.7 换掉 —— 它是**唯一**住着 A_ani 的地方
  python3 - "$A" <<'PY'
import re, sys
A = sys.argv[1]
t = open("case.i", encoding="utf-8").read()
pat = r"\(1\+0\.7\*\(2\*\(gr0\^2/\(gr0\^2\+gr1\^2\+1e-3\)\)-1\)\)"
t2, n = re.subn(pat, f"(1+{A}*(2*(gr0^2/(gr0^2+gr1^2+1e-3))-1))", t)
assert n == 1, f"A={A}：L 表达式里的 0.7 匹配 {n} 处（应为 1）"
open("case.i", "w", encoding="utf-8", newline="").write(t2)
PY
  [ -d "$SEED" ] && { mkdir -p .jitcache; cp -rn "$SEED"/. .jitcache/ 2>/dev/null || true; }
  S=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i case.i Executioner/end_time=$END > run.log 2>&1 || RC=$?
  printf "  A=%-7s rc=%-4s %4ss\n" "$A" "$RC" "$(( $(date +%s) - S ))"
  cd "$ROOT"
done

echo
echo "=== 结果：gr0 的面积分数（对齐晶粒占多少）==="
python3 "$HERE/_ani_cg_report.py" "$ROOT" "$ANI_LIST"
