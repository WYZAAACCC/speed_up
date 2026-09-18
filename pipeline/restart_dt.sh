#!/bin/bash
# 【统一修正起始 dt 后重启受影响的测量】
#
# 发现的问题：起始 dt 给太大（1e-6 ~ 4e-6），而首步实际阈值在 5e-7 左右。
# 后果：首步反复失败、疯狂砍步长，全尺寸那次白烧了 2839 s（47 分钟）。
# 这不是物理问题，是配置问题 —— 起始 dt 给 1e-7，让 IterationAdaptiveDT
# （growth_factor=1.5）自己爬上去即可。
#
# 重启 bench_full（要干净的单步耗时）与 mpi_scale、diag_scale。
# **不动 D**（ASM+1e-9）—— 它已从 dt=1e-6 起步并靠自己砍到 5e-7 正常推进了。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

echo "=== 停掉受影响的作业（保留 D）==="
for P in $(pgrep -f 'bench.i'); do echo "  杀 bench.i PID=$P"; kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'mpi.i');   do echo "  杀 mpi.i   PID=$P"; kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'g_lo.i');  do kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'g_hi.i');  do kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'bf.sh');   do kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'ms.sh');   do kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'dgs.sh');  do kill -9 "$P" 2>/dev/null; done
sleep 3
echo "  剩余 MOOSE: $(ps -eo comm | grep -c phase_field)"

# ---- 1. MPI 扩展性（改成 dt=1e-7）----
sed 's/\r$//' /mnt/f/speed_up/pipeline/mpi_scale.sh > /root/work/ms.sh
python3 - <<'PY'
import re
p = "/root/work/ms.sh"
s = open(p, encoding="utf-8").read()
s = s.replace('s = re.sub(r"^    dt = .*$", "    dt = 4e-6", s, flags=re.M)',
              's = re.sub(r"^    dt = .*$", "    dt = 1e-7", s, flags=re.M)')
open(p, "w", encoding="utf-8").write(s)
print("  ms.sh: 起始 dt -> 1e-7")
PY
nohup bash /root/work/ms.sh > /root/work/ms.log 2>&1 &
echo "  已重启 MPI 扩展性测试"

# ---- 2. 逐变量残差诊断（改成 dt=1e-7）----
sed 's/\r$//' /mnt/f/speed_up/pipeline/diag_scaling.sh > /root/work/dgs.sh
python3 - <<'PY'
import re
p = "/root/work/dgs.sh"
s = open(p, encoding="utf-8").read()
s = s.replace('s = re.sub(r"^    dt = .*$", "    dt = 4e-6", s, flags=re.M)',
              's = re.sub(r"^    dt = .*$", "    dt = 1e-7", s, flags=re.M)')
s = s.replace('s = re.sub(r"^  end_time = .*$", "  end_time = 8e-6", s, flags=re.M)',
              's = re.sub(r"^  end_time = .*$", "  end_time = 4e-6", s, flags=re.M)')
open(p, "w", encoding="utf-8").write(s)
print("  dgs.sh: 起始 dt -> 1e-7, end_time -> 4e-6")
PY
nohup bash /root/work/dgs.sh > /root/work/dgs.log 2>&1 &
echo "  已重启逐变量残差诊断"

# ---- 3. 全尺寸基准（改成 dt=1e-7，只跑 2 步拿干净的单步耗时）----
sed 's/\r$//' /mnt/f/speed_up/pipeline/bench_full_mumps.sh > /root/work/bf.sh
python3 - <<'PY'
import re
p = "/root/work/bf.sh"
s = open(p, encoding="utf-8").read()
s = s.replace('s = re.sub(r"^    dt = .*$",      "    dt = 4e-6", s, flags=re.M)',
              's = re.sub(r"^    dt = .*$",      "    dt = 1e-7", s, flags=re.M)')
open(p, "w", encoding="utf-8").write(s)
print("  bf.sh: 起始 dt -> 1e-7")
PY
nohup bash /root/work/bf.sh > /root/work/bf.log 2>&1 &
echo "  已重启全尺寸基准"

sleep 10
echo
echo "=== 当前进程 ==="
for P in $(pgrep -f phase_field-opt); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-i [^ ]+')
  echo "  PID=$P  $CMD"
done
