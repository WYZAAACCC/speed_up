#!/bin/bash
# =============================================================================
# 建/更新自建 MOOSE app（GbJac）并把 ACGrGrPolyJ 编进去
# =============================================================================
#
# 为什么需要自建 app：
#   MOOSE 上游 `ACGrGrPoly` 的雅可比不全（详见 include/kernels/ACGrGrPolyJ.h
#   的文件头）。要修就必须加一个 C++ 核。MOOSE 的规矩是自定义核放在自己的
#   app 里，**不动 /root/moose 的安装**——这样 MOOSE 保持原版、
#   与 VALIDATION_STATUS.md 里记录的版本号/SHA 一致，可复现。
#
# 用法（在 WSL 里）：
#     bash build_app.sh              # 首次建（约 5-15 分钟）
#     bash build_app.sh              # 只改过核文件时（增量，约 1 分钟）
#
# 建成后可执行文件：/root/projects/gb_jac/gb_jac-opt
# 跑算例时把 phase_field-opt 换成它即可（它已包含 phase_field 全部对象）。
#
# ⚠ 本机 MOOSE 的构建方式（踩过才写下来）：
#   源码是 `git clone` **不含子模块**的，libMesh / PETSc / WASP 全部来自
#   conda 的 moose-dev 包。三者的位置由**激活 conda 环境**时设置的环境变量
#   （LIBMESH_DIR / PETSC_DIR / WASP_DIR）指定。
#   不激活就直接 make 会报：
#       libmesh-config: not found
#       ***ERROR*** WASP does not seem to be available.
#   这两个错**与核代码无关**，纯粹是环境没激活。
# =============================================================================

# ⚠ 不用 `set -u`：conda 的 activate 脚本会引用未定义的 $CONDA_BUILD，
#   set -u 会让它直接退出（本项目已踩过一次）。
set -eo pipefail

APP_DIR=/root/projects/gb_jac
MOOSE_DIR=/root/moose
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- 0. 激活 conda 环境（不激活则找不到 libmesh-config / WASP）---
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
for v in LIBMESH_DIR PETSC_DIR WASP_DIR; do
  eval "val=\${$v:-}"
  if [ -z "$val" ]; then
    echo "错误：conda 环境里 $v 未设置（moose-dev 包是否装好？），拒绝继续" >&2
    exit 1
  fi
  echo "  $v = $val"
done

if [ ! -d "$APP_DIR" ]; then
  echo "== 首次创建 app 骨架 =="
  mkdir -p /root/projects
  cd /root/projects
  "$MOOSE_DIR/scripts/stork.sh" GbJac >/dev/null
fi

cd "$APP_DIR"

# --- 1. 同步核文件 ---
mkdir -p include/kernels src/kernels
cp "$SRC_DIR/include/kernels/ACGrGrPolyJ.h" include/kernels/
cp "$SRC_DIR/src/kernels/ACGrGrPolyJ.C"     src/kernels/

# --- 2. 修 stork 生成的两个问题（幂等）---
# (a) main.C 引用的是 test app 的头文件（stork 的 bug），主 app 该用 GbJacApp
sed -i 's/GbJacTestApp/GbJacApp/g' src/main.C

# (b) 打开 PHASE_FIELD 模块依赖
sed -i 's/^PHASE_FIELD *:= *no/PHASE_FIELD                 := yes/' Makefile
grep -q '^PHASE_FIELD *:= *yes' Makefile || {
  echo "错误：Makefile 里 PHASE_FIELD 没打开成功，拒绝继续" >&2; exit 1; }

# --- 3. 编译 ---
export MOOSE_DIR
JOBS="${JOBS:-8}"
LOG="${LOG:-/tmp/gbjac_build.log}"
echo "== 编译（MOOSE_DIR=$MOOSE_DIR, -j$JOBS）=="
METHODS=opt make -j"$JOBS" > "$LOG" 2>&1 && RC=0 || RC=$?
if [ "$RC" -ne 0 ]; then
  echo "编译失败（退出码 $RC），错误摘要："
  grep -nE "error:|Error [0-9]|fatal error" "$LOG" | head -25
  echo "完整日志：$LOG"
  exit "$RC"
fi
echo "== 完成 =="
ls -la "$APP_DIR/gb_jac-opt"
echo
echo "自检（应列出 ACGrGrPolyJ）："
"$APP_DIR/gb_jac-opt" --list-constructed-objects 2>/dev/null | grep -i "ACGrGrPoly" || true
