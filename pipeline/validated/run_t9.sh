#!/bin/bash
# =============================================================================
# T9：三叉晶界 —— 三叉角是否收敛到 120°
# =============================================================================
# 审计判据：「三晶粒静态 | 三叉角误差 ≤ 5°；无伪第三相增长」
#
# 物理：三条晶界能相等时，力平衡要求三个夹角都是 **120°**。
#       这是纯几何结论，**与迁移率无关** —— 所以调 M 只改变快慢，不改变答案。
#
# 设计要点见 validated/make_t9.py 的文件头（两条：种子三角形必须锐角；
# 初始三叉角 = 180° − 三角形内角）。
#
# ⚠ 默认用 **eq17**（等边三角形、相对网格旋转 17°），不用 s1。
#   s1（不等边）是有界域里的非静态构型，角度会随粗化漂移（见 VALIDATION_STATUS §T9），
#   拿它当默认会让人以为测试"应该"通过而实际永远不通过。
#   eq17 的初始角精确 120°×3，是**唯一**能干净测"数值各向异性"的构型（判据 ≤ 5°）。
#
# 用法：
#   bash run_t9.sh                    # 默认 eq17，跑 2e-3 s
#   TRI=s1 T_END=1e-3 bash run_t9.sh  # 换构型/时间
# =============================================================================
set +u   # conda activate 引用未定义的 $CONDA_BUILD

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t9}"
TRI="${TRI:-eq17}"
T_END="${T_END:-2.0e-3}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"

echo "=== 生成 ==="
python3 "$HERE/make_t9.py" --out "$ROOT/t9.i" --seeds-out "$ROOT/seeds3.csv" \
    --tri "$TRI" --t-end "$T_END" 2>&1 | tee "$ROOT/gen.log"
echo

echo "=== 跑 ==="
RC=0
( cd "$ROOT" && /usr/bin/time -f "  墙钟 %e s" "$MOOSE" -i t9.i \
    > run.log 2>&1 ) || RC=$?
echo "  退出码=$RC  警告=$(sed "s/\x1b\[[0-9;]*m//g" "$ROOT/run.log" | grep -ac 'Missing coupled')"
if [ $RC -ne 0 ]; then
  sed "s/\x1b\[[0-9;]*m//g" "$ROOT/run.log" | grep -A5 -m1 "ERROR" | head -8
  exit 1
fi

echo
echo "=== 伪第三相判据（Ση² ≤ 1）==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/validated")
try:
    from robust_csv import read_rows
except Exception:
    def read_rows(p): return list(csv.DictReader(open(p)))
f = os.path.join(sys.argv[1], "t9_out.csv")
r = read_rows(f)
if not r:
    sys.exit("没有 t9_out.csv")
mx = max(float(x.get("sumEta2_max", 0)) for x in r if x.get("sumEta2_max"))
mn = min(float(x["sumEta2_min"]) for x in r if x.get("sumEta2_min"))
print("  max(Ση²) = %.6f   （判据 ≤ 1）   %s" % (mx, "OK" if mx <= 1.0 else "**超 1，有伪第三相**"))
print("  min(Ση²) = %.6f   （三叉点理论值 3/7 = 0.4286）" % mn)
PY

echo
echo "=== 三叉角 ==="
python3 "$HERE/analyze_t9.py" "$ROOT/t9_exo.e" 2>&1 | tail -20

echo
echo "=== 收敛过程（抽样时间步）==="
python3 "$HERE/analyze_t9.py" "$ROOT/t9_exo.e" --times 2>&1 | tail -18
