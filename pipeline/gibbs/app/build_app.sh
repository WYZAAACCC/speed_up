#!/bin/bash
# =============================================================================
# 建/更新 Gibbs 自建 app，把 ScaledTimeDerivative 编进去
# =============================================================================
#   app 名   : Gibbs        ⇒ 可执行文件 /root/projects/gibbs/gibbs-opt
#   注册命名空间: GibbsApp
#
# ⚠ **与生产的 GbJac app 完全隔离**（/root/projects/gb_jac/gb_jac-opt 不碰）。
#   本脚本开工前后都会打印生产二进制的 mtime+sha，确保它没被动过。
#
# ⚠ 本机 MOOSE 无子模块：libMesh/PETSc/WASP 来自 conda 的 moose-dev，
#   位置由**激活 conda 环境**时设置的环境变量指定。不激活就 make 会报
#   "libmesh-config: not found" / "WASP does not seem to be available"
#   —— 这两个错与核代码无关。
#
# 用法： bash build_app.sh
# =============================================================================
set -eo pipefail

APP_DIR=/root/projects/gibbs
APP_NAME=Gibbs
PROD_BIN=/root/projects/gb_jac/gb_jac-opt
MOOSE_DIR=/root/moose
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 文档的标准流程是把脚本 sed 到 /tmp 再跑，那时 $SRC_DIR 会变成 /tmp。加回退。
[ -f "$SRC_DIR/include/kernels/ScaledCoupledTimeDerivative.h" ] || SRC_DIR="/mnt/f/speed_up/pipeline/gibbs/app"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
for v in LIBMESH_DIR PETSC_DIR WASP_DIR; do
  eval "val=\${$v:-}"
  [ -n "$val" ] || { echo "错误：$v 未设置（moose-dev 装好了吗？）" >&2; exit 1; }
  echo "  $v = $val"
done

echo "== 生产二进制（改动前）=="
ls -la "$PROD_BIN"; sha256sum "$PROD_BIN"

if [ ! -d "$APP_DIR" ]; then
  echo "== 首次创建 app 骨架（stork.sh $APP_NAME）=="
  mkdir -p /root/projects
  cd /root/projects
  "$MOOSE_DIR/scripts/stork.sh" "$APP_NAME" >/dev/null
fi

cd "$APP_DIR"
mkdir -p include/kernels src/kernels
cp "$SRC_DIR/include/kernels/ScaledTimeDerivative.h" include/kernels/
cp "$SRC_DIR/src/kernels/ScaledTimeDerivative.C"     src/kernels/
mkdir -p include/constraints src/constraints
cp "$SRC_DIR/include/kernels/ScaledCoupledTimeDerivative.h" include/kernels/
cp "$SRC_DIR/src/kernels/ScaledCoupledTimeDerivative.C"     src/kernels/
cp "$SRC_DIR/include/kernels/ConstAdvection.h" include/kernels/
cp "$SRC_DIR/src/kernels/ConstAdvection.C"     src/kernels/
cp "$SRC_DIR/include/constraints/GBFluxExchange.h" include/constraints/
cp "$SRC_DIR/src/constraints/GBFluxExchange.C"     src/constraints/
mkdir -p include/userobjects src/userobjects
cp "$SRC_DIR/include/userobjects/GBSoluteSink.h" include/userobjects/
cp "$SRC_DIR/src/userobjects/GBSoluteSink.C"     src/userobjects/
cp "$SRC_DIR/include/userobjects/GBStaggeredUpdate.h" include/userobjects/
cp "$SRC_DIR/src/userobjects/GBStaggeredUpdate.C"     src/userobjects/

# stork 生成的两个坑（幂等修）：
#  (a) main.C 引用的是 test app 头文件
sed -i "s/${APP_NAME}TestApp/${APP_NAME}App/g" src/main.C
#  (b) 打开 PHASE_FIELD 模块依赖
sed -i 's/^PHASE_FIELD *:= *no/PHASE_FIELD                 := yes/' Makefile
grep -q '^PHASE_FIELD *:= *yes' Makefile || { echo "错误：PHASE_FIELD 没打开" >&2; exit 1; }

export MOOSE_DIR
JOBS="${JOBS:-8}"
LOG="${LOG:-/tmp/gibbs_build.log}"
echo "== 编译 ($APP_DIR, -j$JOBS) =="
METHODS=opt make -j"$JOBS" > "$LOG" 2>&1 && RC=0 || RC=$?
if [ "$RC" -ne 0 ]; then
  echo "编译失败 rc=$RC，错误摘要："
  grep -nE "error:|Error [0-9]|fatal error" "$LOG" | head -30
  echo "完整日志：$LOG"; exit "$RC"
fi
echo "== 完成 =="
ls -la "$APP_DIR/gibbs-opt"
echo
echo "自检（应列出 ScaledTimeDerivative）："
"$APP_DIR/gibbs-opt" --list-constructed-objects 2>/dev/null | grep -iE "ScaledTimeDerivative|ScaledCoupledTimeDerivative" || echo "  ⚠ 没找到！"
echo
echo "== 生产二进制（改动后，应与上面逐位相同）=="
ls -la "$PROD_BIN"; sha256sum "$PROD_BIN"
