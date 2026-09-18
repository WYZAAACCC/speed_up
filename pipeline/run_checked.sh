#!/bin/bash
# =============================================================================
# 带 CLI 预检的运行器
# =============================================================================
#
# 用法：
#     bash run_checked.sh <input.i> [任意 MOOSE CLI 覆盖 ...]
#
# 例：
#     bash run_checked.sh N.i Mesh/gen/nx=86 Mesh/gen/ny=30 Executioner/end_time=2e-5
#
# -----------------------------------------------------------------------------
# 【为什么需要它】—— 这是一个真金白银烧过机时的坑
# -----------------------------------------------------------------------------
# MOOSE 对"未使用的 CLI 参数"的检查发生在 **`MooseApp::executeExecutioner()`
# 之后**（`MooseApp::errorCheck()`）。也就是说：
#
#     写错一个参数名 -> MOOSE 不会立刻报错 -> 它会**跑完整条算例**
#     -> 然后在收尾时报 `unused parameter` 并 Abort(1)
#
# 本项目实测踩过：把 `Mesh/gen/nx=86` 误写成 `Mesh/nx=86`
# （网格是生成器链，nx 属于 `Mesh/gen/`，不属于 `Mesh/`），
# 于是 MOOSE 用**全尺寸 64500 单元**而不是预期的 2580 单元跑了 2 分钟才被杀。
# 若那是 Gate 1 的参数扫描，每一步都会白烧。
#
# 更糟的是：`Mesh/nx` 这种拼写**看起来完全合理**，肉眼看不出问题。
#
# -----------------------------------------------------------------------------
# 【本脚本做什么】
#   1. 先用 `--mesh-only` 跑一遍**完全相同的 CLI 覆盖** —— 几秒到几十秒，
#      但会做完输入解析，因此能触发"未使用参数"检查。
#   2. 预检通过才跑真算例；不通过立刻退出，不浪费机时。
#
# 【实测依据】
#   `--mesh-only` 确实会触发该检查：
#       $ phase_field-opt -i N.i Mesh/nx=86 --mesh-only
#       -> CLI_ARGS:1.1: unused parameter 'Mesh/nx'
#          Abort(1)
#   而正确的 `Mesh/gen/nx=86` 通过，并产出 num_elem = 2580 的网格。
# =============================================================================

set -o pipefail

if [ $# -lt 1 ]; then
  echo "用法: bash run_checked.sh <input.i> [MOOSE CLI 覆盖 ...]" >&2
  exit 2
fi

INPUT="$1"; shift
OVERRIDES=("$@")

MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
if [ ! -x "$MOOSE" ]; then
  echo "错误：找不到 MOOSE 可执行文件：$MOOSE" >&2
  exit 1
fi

echo "=============================================================="
echo "CLI 预检：$INPUT"
echo "  覆盖参数：${OVERRIDES[*]:-（无）}"
echo "=============================================================="

# --- 1. 预检 ---
PRE_LOG=".precheck_$$.log"
"$MOOSE" -i "$INPUT" "${OVERRIDES[@]}" --mesh-only > "$PRE_LOG" 2>&1
PRE_RC=$?

if [ $PRE_RC -ne 0 ]; then
  echo "❌ 预检失败（退出码 $PRE_RC）——**没有启动真算例**，机时未浪费。"
  echo
  sed 's/\x1b\[[0-9;]*m//g' "$PRE_LOG" | grep -iE 'unused parameter|error|abort' | head -10
  echo
  echo "（完整预检日志：$PRE_LOG）"
  echo
  echo "提示：网格生成器链下，nx/ny 属于 'Mesh/<生成器名>/'，不是 'Mesh/'。"
  echo "      用错名字时 MOOSE 只会在跑完之后才报 unused parameter。"
  exit 1
fi

# 顺便把网格规模打出来 —— 这是"覆盖是否真的生效"的自检
ELEMS=$(sed 's/\x1b\[[0-9;]*m//g' "$PRE_LOG" | grep -oP 'Elems:\s+\K\d+' | tail -1)
echo "✅ 预检通过（Elems = ${ELEMS:-?}）"
echo "   ⚠ 请确认这个单元数是你想要的 —— 若与预期不符，说明某个覆盖没生效"
rm -f "$PRE_LOG"
echo

# --- 2. 真跑 ---
echo "=============================================================="
echo "开始正式运行"
echo "=============================================================="
"$MOOSE" -i "$INPUT" "${OVERRIDES[@]}"
RC=$?
echo
echo "正式运行退出码：$RC"
exit $RC
