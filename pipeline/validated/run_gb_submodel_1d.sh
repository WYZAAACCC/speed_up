#!/bin/bash
# =============================================================================
# 1D 晶界子模型可行性验证   （HANDOFF_2026-09-20.md §5「第 1 步」）
# =============================================================================
# 要回答的问题
# ------------
#   熔池尺度上 wGB = 4 um => 富集比 s = 1.0015，而真实 Ti64 晶界要 3~10。
#   把 wGB 缩到 nm 尺度、域缩到 100 nm 量级的**独立小算例**里，
#   s 能不能回到 3~10 ？（即：弥散界面在小域里还行不行）
#
# 两级判据
# --------
#   主判据   wgb = 2 nm 时  s = c_GB / c_far  落在 3~10 ？
#   标度判据 (s-1)*wgb 是不是常数？三个候选值：
#        闭式(h_gb 峰值取 4，gb_width_vs_s.py 的约定) : 6.1728e-9
#        闭式(峰值取 1，make_1d_gb.py 的 tanh 剖面)   : 1.5432e-9
#        T11 实测锚定（wGB=0.4 um 档反解）            : 1.3533e-9
#      后两者只差 14%，与第一支差 4 倍 —— 本算例直接判决哪一支对。
#
# 读法（AGENTS.md 教训 20）
#   s 从**剖面**读（c_max / c_edge），不从守恒量的差反推。
#   参考值用 c_edge（远场当前值），不用初值 c_grain —— 封闭系统里
#   int(c - c_grain)dx 恒等于 0（晶界富集与旁边贫化正好抵消）。
#
# t_end 必须随 wgb^2 标度（晶界填充时间 tau_fill ~ wgb^2/D_GB），
#   否则薄晶界那几档根本没到平衡。
#
# 用法： bash run_gb_submodel_1d.sh
# =============================================================================
set +u    # conda activate 引用了未定义的 $CONDA_BUILD，开 set -u 会静默退出

HERE="$(cd "$(dirname "$0")" && pwd)"
# 文档的标准流程是把本脚本 sed 到 /tmp 再跑（ENVIRONMENT.md 二），
# 那时 $HERE 会变成 /tmp、找不到同目录的 make_1d_gb.py。加一条回退。
if [ ! -f "$HERE/make_1d_gb.py" ]; then
  HERE="/mnt/f/speed_up/pipeline/validated"
fi
ROOT="${ROOT:-/root/work/gb_sub1d}"
OMEGA0="${OMEGA0:--5e-11}"   # 生产值（已对标 Tan 2016 锚点）
FPART="${FPART:-h_solid}"    # 生产用 min(1,2S) = h_solid
KC="${KC:-1e-14}"            # 生产值
DL="${DL:-2.52e-9}"          # 真实 Ti64 液相扩散系数
DS="${DS:-4.0e-13}"
DGB="${DGB:-4.0e-10}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"

rm -rf "$ROOT"; mkdir -p "$ROOT"

echo "=============================================================="
echo " 1D 晶界子模型可行性验证"
echo " Omega0=$OMEGA0  f_part=$FPART  kappa_c=$KC"
echo " D_L=$DL  D_S=$DS  D_GB=$DGB"
echo "=============================================================="

# tag  dx(nm)  wgb(nm)  ldom(nm)  t_end(s)
# A 组：固定 wgb=2 nm / ldom=100 nm，只扫 dx  -> 判据：s 对 dx 收敛
# B 组：固定 wgb/dx=8、ldom=50*wgb，扫 wgb   -> 判据：(s-1)*wgb 是否常数
CASES=(
  "A_dx1.000nm     1.000   2.0   100  2.0e-6"
  "A_dx0.500nm     0.500   2.0   100  2.0e-6"
  "A_dx0.250nm     0.250   2.0   100  2.0e-6"
  "B_wgb2nm        0.250   2.0   100  2.0e-6"
  "B_wgb4nm        0.500   4.0   200  8.0e-6"
  "B_wgb8nm        1.000   8.0   400  3.2e-5"
  "B_wgb20nm       2.500  20.0  1000  2.0e-4"
  "B_wgb40nm       5.000  40.0  2000  8.0e-4"
)

: > "$ROOT/cases.txt"
for spec in "${CASES[@]}"; do
  set -- $spec
  tag=$1; dx=$2; wgb=$3; ldom=$4; tend=$5
  echo "$tag $dx $wgb $ldom $tend" >> "$ROOT/cases.txt"
  D="$ROOT/$tag"; mkdir -p "$D"
  python3 "$HERE/make_1d_gb.py" --out "$D/gb.i" \
      --dx "${dx}e-9" --wgb "${wgb}e-9" --ldom "${ldom}e-9" --t-end "$tend" \
      --f-part "$FPART" --f-seg "$OMEGA0" \
      --kc "$KC" --dl "$DL" --ds "$DS" --dgb "$DGB" > "$D/gen.log" 2>&1 || {
    echo "$tag: 生成失败"; tail -3 "$D/gen.log"; continue; }
  ( cd "$D" && "$MOOSE" -i gb.i > run.log 2>&1 )
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "$tag: 运行失败 rc=$rc"
    sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -A4 -m1 "ERROR" | head -6
    continue
  fi
  # JIT 静默退化的守卫（ENVIRONMENT.md 三：不激活 conda => rc=0 但慢几十倍）
  njit=$(grep -c "JIT compile failed" "$D/run.log" 2>/dev/null || echo 0)
  nconv=$(grep -c "Solve Did NOT Converge" "$D/run.log" 2>/dev/null || echo 0)
  printf "%-16s dx=%-6s wgb=%-6s ldom=%-6s JIT失败=%s 未收敛=%s\n" \
         "$tag" "$dx" "$wgb" "$ldom" "$njit" "$nconv"
done