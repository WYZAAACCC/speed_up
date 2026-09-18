#!/bin/bash
# 目标降级为**证明 D 版能收敛**（用户要的门槛），把"全量性能"作为独立问题。
#
# 【MPI 实测失败】8 进程 MPI 跑了 25 分钟没走完牛顿迭代 1；单进程 AD+300
#   10 分钟就到迭代 4。所以 MPI 在这套配置下不是加速而是拖慢。
#   可能原因：2D 430x150 网格分 8 份的 halo 通信占比过高、ASM 在 MPI 下的
#   默认 -pc_asm_type basic 开销大、AD 的材料求值本身并行效率低。
#   **未查明，记录为待解决。**
#
# 【全量性能问题】单进程每个牛顿步约 2.5 分钟。全量 end_time=6.5e-4、
#   dtmax=2e-6 需 300+ 步 * 约 3 次牛顿 = 约 40 小时，不可行。
#   这是 AD 版的新代价（L 依赖 8 个 eta + T + 梯度 -> 每单元 44 维对偶数，
#   且解析表达式是解释执行的）。待解决方向见记忆。
#
# 本次：单进程 + l_max_its=1000 + end_time=2e-5（约 10 步）。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_demo

# 停掉 MPI 那跑（它比单进程还慢）
pgrep -f 'phase_field-opt -i' > /tmp/mp.txt 2>/dev/null
xargs -r kill -9 < /tmp/mp.txt 2>/dev/null
sleep 3
echo "已停旧进程，剩余 $(pgrep -cf 'phase_field-opt -i')"

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./C.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("C.i", encoding="utf-8").read()
s = re.sub(r"^  l_max_its = .*$", "  l_max_its = 1000", s, flags=re.M)
s = re.sub(r"^  l_tol = .*$", "  l_tol = 1e-6", s, flags=re.M)
s = re.sub(r"^  end_time = .*$", "  end_time = 2e-5", s, flags=re.M)
s = s.replace("file_base = stage1d", "file_base = C")
# 降 Exodus 输出频率：每步 17 MB，300 步 5 GB，且写盘会拖慢
s = re.sub(r"(time_step_interval = )1\b", r"\g<1>5", s)
if "[Debug]" not in s:
    s = s.replace("\n[Executioner]\n",
                  "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
assert s.count("type = ADGrainGrowth") == 8
open("C.i", "w", encoding="utf-8").write(s)
print("C.i 写好: AD + l_max_its=1000 + end_time=2e-5 + Exodus 每 5 步")
PY

echo "=== 单进程跑 ==="
setsid --wait "$MOOSE" -i C.i > run.log 2>&1 &
MPID=$!
echo "MOOSE pid=$MPID"
# 每 120 秒报一次进度，最多 60 分钟
for k in $(seq 1 30); do
  sleep 120
  NS=$(grep -ac "Solve Converged" run.log 2>/dev/null)
  LAST=$(grep -a "Nonlinear |R|" run.log 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | tail -1)
  TS=$(grep -a "^Time Step" run.log 2>/dev/null | tail -1)
  echo "[$((k*2)) 分钟] 收敛步=$NS | $TS | 末次牛顿: $LAST"
  if ! kill -0 $MPID 2>/dev/null; then echo "MOOSE 已退出"; break; fi
  if [ "$NS" -ge 10 ] 2>/dev/null; then echo "已达 10 步，提前收工"; break; fi
done
echo
echo "=== 最终状态 ==="
grep -ac "Solve Converged" run.log
grep -a "^Time Step" run.log | tail -6 | sed 's/^/  /'
grep -a "Linear solve" run.log | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' | sort | uniq -c | sort -rn | head -4 | sed 's/^/  /'
grep -a -m3 -E '\*\*\* ERROR|Aborting' run.log | sed 's/^/  /'
