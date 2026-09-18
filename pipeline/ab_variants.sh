#!/bin/bash
# 消融 A/B：把"2a 的哪一半 / 2b"逐个关掉，用同一个仪器看首步雅可比能不能解。
#
# 关键观测（已在 try2/try3 上确认）：首步 dt 从 1e-6 一路砍到 6.25e-8 **全部失败**。
# 缩小 dt 不能改善 => 问题不在非线性/刚性的时间积分，而在**初始状态的雅可比本身**。
# 所以对照实验都用 end_time=1e-6（只跑首步）+ show_var_residual_norms。
#
# 运行 5 个：
#   C    stage1_meltpool_c.i 原样（已验证能收敛的基线）
#   v0   D 版原样（已知卡）
#   v1   关 2b（L2b 恒为 1）          <- 最关键的一个
#   v2   关 L 的取向依赖（各向同性 Arrhenius）
#   v3   关 kappa/gamma 的取向依赖（回常数）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
SRC=/mnt/f/speed_up/pipeline
D=/root/work/s1d_ab
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
for f in stage1_meltpool_c.i stage1_meltpool_d.i make_variants.py columnar_seeds.csv; do
  sed 's/\r$//' "$SRC/$f" > "$f"
done

python3 make_variants.py || exit 1

# 给每个 .i 加逐变量残差诊断；统一 end_time=1e-6
python3 - <<'PY'
import re
DBG = "[Debug]\n  show_var_residual_norms = true\n[]\n"
for tag in ("C", "v0", "v1", "v2", "v3"):
    fn = "stage1_meltpool_c.i" if tag == "C" else f"{tag}.i"
    s = open(fn, encoding="utf-8").read()
    s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
    if "[Debug]" not in s:
        s = s.replace("\n[Executioner]\n", "\n" + DBG + "[Executioner]\n", 1)
    s = s.replace("print_linear_residuals = false", "print_linear_residuals = true")
    out = f"{tag}_ab.i"
    open(out, "w", encoding="utf-8").write(s)
    print(f"  {out}")
PY

# 每个跑在独立的干净目录里（各自都要 columnar_seeds.csv）
for t in C v0 v1 v2 v3; do
  mkdir -p "$t"; cp "${t}_ab.i" columnar_seeds.csv "$t"/
done

echo "=== 并行启动 (5 个进程 / 20 核) ==="
for t in C v0 v1 v2 v3; do
  ( cd "$D/$t" && setsid --wait "$MOOSE" -i "${t}_ab.i" > run.log 2>&1; \
    echo "  $t 结束 rc=$?" ) &
done
wait
echo "=== 全部结束 ==="
