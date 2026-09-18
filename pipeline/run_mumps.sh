#!/bin/bash
# MUMPS 直接解测试：完整配置（215x75，8 序参量，约 18 万自由度）能否**正确收敛**。
#
# 【为什么试 MUMPS】今天两个"通过"的测试（最小竞争生长算例、J 级 8 序参量）
# 用的都是 MUMPS；而所有卡住的场景用的都是 ASM/ILU。残差地板（非 AD 卡 7e-7）
# 与"牛顿爬行"（AD 每步只降 0.1%）根子上都是**线性求解没解准**。
# MUMPS 做精确 LU -> 牛顿拿到真实步长 -> 应为二次收敛、无地板。
#
# 【内存是唯一会崩的风险】MUMPS 的 fill-in 远多于原矩阵。18 万自由度 2D 我估计
# 需要几 GB，但**没有把握**。所以：
#   * 先并行跑 2 个（serial AD + serial 非AD），不贪多
#   * 带**内存看门狗**：可用内存低于阈值就杀掉最晚启动的那个，避免 OOM 拖垮 WSL
#     （今天已经因为 kill -9 一批进程把 WSL 搞崩过一次，E_UNEXPECTED）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_mumps

# 停掉两个 ASM 跑（结论已取到：C_ad 砍步长、C_nonad 残差 4.01e-10）
pgrep -f 'phase_field-opt -i' > /tmp/mp.txt 2>/dev/null
xargs -r kill -9 < /tmp/mp.txt 2>/dev/null
sleep 4
echo "已停旧进程，剩余 $(ps -eo comm | grep -c phase_field)；可用内存 $(free -g | awk 'NR==2{print $7}') GB"

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_full/C_ad.i    ./M1_src.i
cp /root/work/s1d_full/C_nonad.i ./M2_src.i
cp /root/work/s1d_full/columnar_seeds.csv .

python3 - <<'PY'
import re
for src, dst, tag in (("M1_src.i", "M1.i", "M1"), ("M2_src.i", "M2.i", "M2")):
    s = open(src, encoding="utf-8").read()
    s = re.sub(r"^  petsc_options_iname = .*$",
               "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -pc_factor_shift_type'",
               s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$",
               "  petsc_options_value = 'lu mumps nonzero'", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 4e-5", s, flags=re.M)
    s = s.replace("file_base = Cad", f"file_base = {tag}").replace("file_base = Cnonad", f"file_base = {tag}")
    assert "type = TimeDerivative" in s or "ADTimeDerivative" in s
    open(dst, "w", encoding="utf-8").write(s)
    ad = "ADGrainGrowth" in s
    print(f"  {dst}: AD={ad}  pc_type=lu(mumps)")
PY

for t in M1 M2; do mkdir -p "$t"; cp "${t}.i" columnar_seeds.csv "$t"/; done

echo "=== 启动 M1(AD+MUMPS) / M2(非AD+MUMPS) ==="
( cd M1 && setsid --wait "$MOOSE" -i M1.i > run.log 2>&1; echo "M1 rc=$?" > /root/work/mumps_rc.txt ) &
( cd M2 && setsid --wait "$MOOSE" -i M2.i > run.log 2>&1; echo "M2 rc=$?" >> /root/work/mumps_rc.txt ) &

# 内存看门狗：每 30 秒查一次，低于 2 GB 就杀最晚启动的那个 MOOSE
for k in $(seq 1 120); do
  sleep 30
  AV=$(free -g | awk 'NR==2{print $7}')
  NP=$(ps -eo comm | grep -c phase_field)
  if [ -n "$AV" ] && [ "$AV" -lt 2 ] 2>/dev/null; then
    NEWEST=$(pgrep -f 'phase_field-opt -i' | tail -1)
    echo "[看门狗] 可用内存仅 ${AV} GB，杀掉最新进程 $NEWEST"
    kill -9 "$NEWEST" 2>/dev/null
    sleep 5
  fi
  # 跑到两个都结束就退出
  [ "$(ps -eo comm | grep -c phase_field)" -eq 0 ] && { echo "[看门狗] 全部结束"; break; }
done

wait
echo
echo "================= MUMPS 结果 ==================="
for t in M1 M2; do
  L="/root/work/s1d_mumps/$t/run.log"
  echo "--- $t ---"
  echo "  收敛步=$(grep -ac 'Solve Converged' "$L" 2>/dev/null | head -1)"
  echo "  牛顿轨迹:"
  grep -a "Nonlinear |R|" "$L" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | tail -10 | sed 's/^/    /'
  echo "  时间步:"
  grep -a "^Time Step" "$L" 2>/dev/null | tail -4 | sed 's/^/    /'
  echo "  报错:"
  grep -a -m3 -E '\*\*\* ERROR|out of memory|Aborting' "$L" 2>/dev/null | sed 's/^/    /'
done
echo "--- 内存峰值参考 ---"
free -g | head -2
