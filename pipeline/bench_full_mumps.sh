#!/bin/bash
# 【规划输入 1】全尺寸（430x150, dx=1um）非 AD + MUMPS 的内存与单步耗时实测。
#
# 为什么必须先测：M2（215x75）MUMPS 只用 486 MB、94 s/步，但全尺寸单元数 4 倍，
# MUMPS 的 fill-in 在 2D 上约 O(N log N)，**外推不可靠**（可能 2 GB 也可能 15 GB）。
# 内存是唯一会拖垮 WSL 的风险，所以带 RSS 看门狗。
#
# 只跑 2 个时间步：MUMPS 的内存峰值出现在第一次分解，1 步就够；2 步拿到稳的每步耗时。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/bench_full
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_full/C_nonad.i src.i
cp /root/work/s1d_full/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("src.i", encoding="utf-8").read()
s = re.sub(r"^    nx = .*$", "    nx = 430", s, flags=re.M)
s = re.sub(r"^    ny = .*$", "    ny = 150", s, flags=re.M)
s = re.sub(r"^  petsc_options_iname = .*$",
           "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -pc_factor_shift_type'",
           s, flags=re.M)
s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps nonzero'", s, flags=re.M)
s = re.sub(r"^  end_time = .*$",  "  end_time = 8e-6", s, flags=re.M)
s = re.sub(r"^  dtmax = .*$",     "  dtmax = 4e-6", s, flags=re.M)
s = re.sub(r"^    dt = .*$",      "    dt = 4e-6", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 15", s, flags=re.M)
s = s.replace("file_base = Cnonad", "file_base = bf")
# 关掉 Exodus 输出，避免写盘干扰耗时测量
s = re.sub(r"(\[Outputs\][\s\S]*?)\[\]\s*$", r"\1[]", s)
open("bench.i", "w", encoding="utf-8").write(s)
print("  网格 =", re.search(r"^    nx = (\d+)", s, flags=re.M).group(1), "x",
      re.search(r"^    ny = (\d+)", s, flags=re.M).group(1))
PY

echo "=== 启动全尺寸 MUMPS 基准（430x150），RSS 看门狗阈值 9 GB ==="
setsid --wait "$MOOSE" -i bench.i > run.log 2>&1 &
MPID=$!
PEAK=0
while kill -0 $MPID 2>/dev/null; do
  for P in $(pgrep -f 'phase_field-opt -i bench.i' 2>/dev/null); do
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    [ -n "$R" ] && [ "$R" -gt "$PEAK" ] 2>/dev/null && PEAK=$R
    if [ -n "$R" ] && [ "$R" -gt 9000000 ] 2>/dev/null; then
      echo "[看门狗] RSS 超过 9 GB（${R} kB），杀掉 $P"
      kill -9 $P 2>/dev/null
    fi
  done
  sleep 4
done
wait $MPID
RC=$?

echo
echo "================ 全尺寸 MUMPS 基准结果 ================"
echo "  退出码 = $RC"
echo "  **RSS 峰值 = $((PEAK/1024)) MB**"
echo "  --- MOOSE 自报内存（末 5 行）---"
grep -a -oE '\[ *[0-9]+ MB\]' run.log | tail -5 | sed 's/^/    /'
echo "  --- 每步耗时 ---"
grep -a -E 'Solve Converged|Finished Solving' run.log | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^/    /'
echo "  --- 牛顿末 10 次 ---"
grep -a 'Nonlinear |R|' run.log | sed 's/\x1b\[[0-9;]*m//g' | tail -10 | sed 's/^/    /'
echo "  --- 报错 ---"
grep -a -m4 -E '\*\*\* ERROR|Aborting|out of memory|Cannot allocate' run.log | sed 's/^/    /'
echo
echo "  对照：215x75 MUMPS = 486 MB / 94 s 每步 / 二次收敛到 4.0e-10"
