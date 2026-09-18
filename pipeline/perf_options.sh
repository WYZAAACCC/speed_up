#!/bin/bash
# 【性能攻坚：MUMPS 分解占了每次牛顿迭代 189 s 中的约 150 s，是绝对瓶颈】
#
# 若 MPI 扩展性不够（2D 的 multifrontal 临界路径长，并行效率通常只有 2-4x），
# 下面是几个**从未试过、成本很低**的旋钮：
#
#   O1  -pc_factor_mat_ordering_type nd      嵌套剖分，2D 网格通常优于默认
#   O2  -pc_factor_mat_ordering_type metis   METIS 填充最小化
#   O3  -pc_factor_mat_ordering_type rcm     反向 Cuthill-McKee（带宽最小）
#   O4  -snes_lag_preconditioner 5           复用分解 5 步（Jacobian 变化不大时省
#                                             掉大部分 150 s）
#   O5  -snes_lag_jacobian 5                 同上，连装配也省
#   O6  O3 + O4 组合
#
# 全部在 215x75 上跑，**统一 end_time / dt / 容差**，只看"每牛顿迭代耗时"和"牛顿迭代数"。
# 判据：能在不显著增加牛顿迭代数的前提下把单迭代耗时压下来的组合胜出。
#
# 【重要】起始 dt 一律 1e-7（见 ROADMAP §3.2 的坑）。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/perf_opt
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/slv_cmp/C/C.i base.i
cp /root/work/slv_cmp/columnar_seeds.csv .

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()

# 变体：(tag, iname 追加项, ivalue 追加项)
VARIANTS = [
    ("P0", "", ""),                                                   # 基线 MUMPS
    ("P1", " -pc_factor_mat_ordering_type", " nd"),                   # 嵌套剖分
    ("P2", " -pc_factor_mat_ordering_type", " metis"),                # METIS
    ("P3", " -pc_factor_mat_ordering_type", " rcm"),                  # RCM
    ("P4", " -snes_lag_preconditioner", " 5"),                        # 复用分解
    ("P5", " -pc_factor_mat_ordering_type -snes_lag_preconditioner", " nd 5"),
]

for tag, ai, av in VARIANTS:
    s = base
    # 统一：短跑，只到 8e-6，起始 dt=1e-7
    s = re.sub(r"^  end_time = .*$", "  end_time = 8e-6", s, flags=re.M)
    s = re.sub(r"^    dt = .*$", "    dt = 1e-7", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 20", s, flags=re.M)
    # 追加 PETSc 选项
    s = re.sub(r"^  petsc_options_iname = '(.*)'$", lambda m: f"  petsc_options_iname = '{m.group(1)}{ai}'", s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = '(.*)'$", lambda m: f"  petsc_options_value = '{m.group(1)}{av}'", s, flags=re.M)
    s = re.sub(r"\[Outputs\][\s\S]*$", "[Outputs]\n  csv = true\n[]\n", s)
    open(f"{tag}.i", "w", encoding="utf-8").write(s)
    print(f"  {tag}.i : iname +='{ai}'  value +='{av}'")
PY

for T in P0 P1 P2 P3 P4 P5; do mkdir -p "$T"; cp "$T.i" columnar_seeds.csv "$T"/; done

echo
echo "=== 依次跑 P0..P5（串行，避免互相干扰）==="
for T in P0 P1 P2 P3 P4 P5; do
  echo "--- $T 开始 $(date +%H:%M:%S) ---"
  cd "$D/$T" || continue
  T0=$(date +%s)
  setsid --wait "$MOOSE" -i "$T.i" > run.log 2>&1
  RC=$?
  T1=$(date +%s)
  NJ=$(grep -ac 'Nonlinear |R|' run.log)
  JC=$(grep -a -oE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' run.log | sed 's/.*\[ *//;s/ s\]//' | awk '{s+=$1;n++} END{if(n>0)printf "%.1f",s/n}')
  echo "  $T rc=$RC 墙钟=$((T1-T0))s 牛顿迭代数=$NJ 雅可比均值=${JC}s"
  cd "$D" || exit 1
done

echo
echo "================ 性能选项汇总 ================"
printf "  %-5s %-10s %-12s %-12s %s\n" "tag" "墙钟(s)" "牛顿迭代数" "雅可比(s)" "每迭代(s)"
for T in P0 P1 P2 P3 P4 P5; do
  L="$D/$T/run.log"
  [ -f "$L" ] || continue
  W=$(grep -aoE 'Finished Executing[^]]*\] \[[^]]*\]' "$L" | head -1 | grep -oE '[0-9.]+' | head -1)
  [ -z "$W" ] && W="?"
  NJ=$(grep -ac 'Nonlinear |R|' "$L")
  JC=$(grep -a -oE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' "$L" | sed 's/.*\[ *//;s/ s\]//' | awk '{s+=$1;n++} END{if(n>0)printf "%.1f",s/n}')
  PI=$(awk -v w="$W" -v n="$NJ" 'BEGIN{if(n>0 && w!="?") printf "%.1f", w/n; else print "?"}')
  printf "  %-5s %-10s %-12s %-12s %s\n" "$T" "$W" "$NJ" "$JC" "$PI"
done
