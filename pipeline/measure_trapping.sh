#!/bin/bash
# 【C4 第一步：测量人为溶质截留】
#
# 原理：抗截留项（AntitrappingCurrent）存在的根本原因，就是**弥散界面在平衡态下
#       给出的分配系数是错的**（界面越宽、相对网格越粗，偏差越大）。
#       所以最直接的测量是：**固定物理界面宽度，改变网格分辨率，量 k 的偏差**。
#
# 本算例把 η 固定成 tanh 剖面（无 η 的核），只让溶质弛豫到平衡
# —— 这正是 verify_partition.i 的做法，与生产算例的 f_loc 形式一致。
#
# 设计：
#   * 物理界面宽 w = 4e-6 m（与生产算例 int_width 一致）
#   * 域长 L = 40e-6 m（留出足够长的固相/液相深部供探测）
#   * 变网格：w/dx = 1, 2, 4, 8, 16  （生产是 w/dx = 4）
#   * 目标 k = 0.63（Ti64 的 V；A_part = 0.264）
#
# 判据：
#   w/dx=4（生产配置）时若 |k_实测 - 0.63| 很小 -> 人为截留可忽略，C4 可暂缓
#                              若明显偏离      -> 必须加抗截留项
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/trap
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

# 基于 verify_partition.i 改造：域长与网格可调
sed 's/\r$//' /mnt/f/speed_up/pipeline/verify_partition.i > base.i

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()

# 固定 k=0.63 的参数
base = base.replace("${k_c}", "0.9").replace("${c0}", "0.036").replace("${A_part}", "0.264")
# 界面位置改到域中心 20e-6，界面半宽 2e-6（tanh 的 1/e 尺度 => 视觉宽度约 4e-6）
base = re.sub(r"0\.5e-6-x", "20e-6-x", base)
base = re.sub(r"/0\.1e-6", "/2e-6", base)
base = re.sub(r"^  xmax = .*$", "  xmax = 40e-6", base, flags=re.M)
base = re.sub(r"^  nx = .*$",   "  nx = PLACEHOLDER", base, flags=re.M)
# 探测点：固相深部与液相深部（按比例，稍后用 elementid 覆盖）
base = re.sub(r"^  end_time = .*$", "  end_time = 1.0", base, flags=re.M)

# 变体：w/dx = 1,2,4,8,16  ->  dx = 4e-6/nx_def
# 【坑】探测单元的替换：原文件里是 `[c_solid]` 块在前、`elementid = 10` 在后，
# 我第一次把正则写成"elementid 后面跟 [c_solid]"，方向反了，导致替换静默失败，
# 探测单元仍是 nx=200 时的 10/190 —— 而 nx=40 时单元 190 不存在，c_liquid 恒为 0。
# 现在直接按**原值**替换（10 -> 固相探测、190 -> 液相探测），无歧义。
VARIANTS = [("c1", 10), ("c2", 20), ("c4", 40), ("c8", 80), ("c16", 160)]
import os
for tag, nx in VARIANTS:
    s = base.replace("PLACEHOLDER", str(nx))
    es = int(nx * 0.15)
    el = int(nx * 0.85)
    assert "elementid = 10" in s and "elementid = 190" in s, "原探测单元值不是 10/190，替换逻辑需更新"
    s = s.replace("elementid = 10", f"elementid = {es}").replace("elementid = 190", f"elementid = {el}")
    os.makedirs(tag, exist_ok=True)
    open(f"{tag}/t.i", "w", encoding="utf-8").write(s)
    print(f"  {tag}: nx={nx}  dx={40e-6/nx*1e6:.2f} um  w/dx={4e-6/(40e-6/nx):.0f}  探测单元 {es}/{el}")
PY

echo
echo "=== 串行跑 5 个分辨率 ==="
for T in c1 c2 c4 c8 c16; do
  ( cd "$T" && setsid --wait "$MOOSE" -i t.i > run.log 2>&1; echo "$T rc=$?" >> "$D/rc.txt" )
done

echo
echo "================ 人为溶质截留测量 ================"
printf "  %-6s %-8s %-8s %-12s %-12s %-10s %s\n" "变体" "nx" "w/dx" "c_solid" "c_liquid" "实测k" "偏差(vs 0.63)"
python3 - <<'PY'
import csv, os
target = 0.63
for tag, nx in (("c1",10),("c2",20),("c4",40),("c8",80),("c16",160)):
    p = f"/root/work/trap/{tag}/t_out.csv"
    if not os.path.exists(p):
        print(f"  {tag:<6} {nx:<8} 无输出"); continue
    rows = list(csv.DictReader(open(p)))
    if not rows: continue
    r = rows[-1]
    cs, cl = float(r["c_solid"]), float(r["c_liquid"])
    k = cs/cl if cl else float("nan")
    dev = (k-target)/target*100
    wdx = 4e-6/(40e-6/nx)
    flag = "" if abs(dev) < 5 else "  <== 偏差显著"
    print(f"  {tag:<6} {nx:<8} {wdx:<8.0f} {cs:<12.6f} {cl:<12.6f} {k:<10.4f} {dev:+7.2f}%{flag}")
PY
echo
echo "  目标 k = 0.63（Ti64 的 V）。生产配置是 w/dx = 4（int_width 4um / dx 1um）。"
echo "  判据：w/dx=4 处偏差小 -> 人为截留可忽略；偏差大 -> 必须加 AntitrappingCurrent。"
