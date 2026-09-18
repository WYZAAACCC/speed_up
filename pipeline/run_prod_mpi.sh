#!/bin/bash
# 生产跑：AD 精确雅可比 + 高线性迭代上限 + **MPI 并行**。
#
# 【为什么必须上 MPI】实测 AD 版每个牛顿步约 2.5 分钟（单进程）。全量
# end_time=6.5e-4、dtmax=2e-6 需 300+ 步、每步约 3 次牛顿 -> 单进程约 40 小时，
# 不可行。这台机器 20 核，MPI 是唯一现实的加速手段（AD 的材料求值是
# 逐单元独立的，并行效率应该不错）。
#
# 配置选择依据：
#   AD + l_max_its=30  -> 牛顿单调下降但 2 次 DIVERGED_ITS 30
#   AD + l_max_its=300 -> 牛顿到迭代 4（3.91->2.75e-05），仍有 2 次 DIVERGED_ITS 300
#   => 线性求解差一点，取 l_max_its=1000 留足余量
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
NP=8

# 停掉批量预条件子测试（-sub_pc_type lu 太慢，25 分钟还没走出牛顿迭代 0）
# 注意：这条 pgrep 放在 .sh 文件里跑 —— 若放在内联命令里，执行它的 shell
# 自身 argv 会含这个模式串，pgrep 会匹配到自己并 kill -9（今天踩过）。
pgrep -f 'phase_field-opt -i' > /tmp/mp.txt 2>/dev/null
xargs -r kill -9 < /tmp/mp.txt 2>/dev/null
sleep 3
echo "已停旧进程，剩余 $(pgrep -cf 'phase_field-opt -i')"
D=/root/work/s1d_prod
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./P.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("P.i", encoding="utf-8").read()
s = re.sub(r"^  l_max_its = .*$", "  l_max_its = 1000", s, flags=re.M)
s = re.sub(r"^  l_tol = .*$", "  l_tol = 1e-6", s, flags=re.M)
# 保留全量 end_time=6.5e-4（不要覆盖！）
assert "end_time = 6.5e-4" in s, "end_time 不是全量，检查输入"
s = s.replace("file_base = stage1d", "file_base = P")
# 输出太频繁会拖慢；每步存 Exodus 但只在 timestep_end
open("P.i", "w", encoding="utf-8").write(s)
print("P.i 写好: AD 核 + l_max_its=1000 + end_time=6.5e-4（全量）")
PY

echo "=== mpiexec 检查 ==="
which mpiexec || ls /root/moose/*/bin/mpiexec 2>/dev/null || echo "未找到 mpiexec"

echo "=== 启动 MPI 生产跑（-n $NP）==="
setsid --wait mpiexec -n $NP "$MOOSE" -i P.i > run.log 2>&1
echo "退出码 $?"
