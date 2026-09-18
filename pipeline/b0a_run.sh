#!/bin/bash
# 跑 B0a 最小实验：澄清 reserve_op 语义。
#
# 判据（看输出的 CSV）：
#   最终 max_gr3 ≈ 1            -> 核留在保留 op 上  -> 保留 op 是**永久槽位**（语义 ii）
#   最终 max_gr3 → 0 且某 op 增大 -> 核被 remap 走    -> 保留 op 是**可复用暂存位**（语义 i）
#
# 另看 n_grains（GrainTracker 看到的晶粒数）是否从 2 变成 3。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/b0a
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

sed 's/\r$//' /mnt/f/speed_up/pipeline/b0a_nucleation.i > b0a.i

cat > nuclei.csv <<'CSV'
time,x,y
0.5,15,15
CSV

echo "=== 输入 ==="
grep -nE "reserve_op|op_num|type = DiscreteNucleation" b0a.i | sed 's/^/  /'
echo "  形核点: $(tail -1 nuclei.csv)"

echo
echo "=== 运行 ==="
setsid --wait "$MOOSE" -i b0a.i > run.log 2>&1
RC=$?
echo "  rc=$RC"

echo
echo "================ B0a 结果 ================"
if [ ! -f b0a_out.csv ]; then
  echo "  没有 CSV 输出，查报错："
  sed 's/\x1b\[[0-9;]*m//g' run.log | grep -aE '\*\*\* ERROR|Aborting|unused|not found' | head -8 | sed 's/^/    /'
  exit 0
fi

echo "  --- 逐时刻各 op 的最大值 ---"
head -1 b0a_out.csv | tr ',' '\n' | grep -nE 'max_gr|n_grains' | sed 's/^/    列 /'
echo
python3 - <<'PY'
import csv
rows = list(csv.DictReader(open("/root/work/b0a/b0a_out.csv")))
if not rows:
    print("  无数据行"); raise SystemExit
keys = [k for k in rows[0] if k.startswith("max_gr")]
gkey = [k for k in rows[0] if "n_grains" in k or k == "n_grains"]
print(f"  {'time':>10}" + "".join(f"{k:>12}" for k in keys) + f"{'晶粒数':>10}")
step = max(1, len(rows) // 12)
for r in rows[::step] + [rows[-1]]:
    line = f"  {float(r['time']):>10.4f}"
    for k in keys:
        line += f"{float(r[k]):>12.4f}"
    if gkey:
        line += f"{float(r[gkey[0]]):>10.0f}"
    print(line)

first, last = rows[0], rows[-1]
print()
print("  ================ 判定 ================")
m3f, m3l = float(first.get("max_gr3", 0)), float(last.get("max_gr3", 0))
print(f"  max_gr3: 初始 {m3f:.4f} -> 最终 {m3l:.4f}")
if m3l > 0.5:
    print("  ==> **核留在保留 op gr3 上** —— reserve_op 是【永久槽位】")
    print("      含义：每个保留 op 只能承载 1 个形核晶粒，且取向固定为该 op 的 θ。")
    print("      路径 A 可行，但形核次数上限 = reserve_op 的个数。")
else:
    print("  ==> **核从 gr3 被 remap 走了** —— reserve_op 是【可复用暂存位】")
    print("      含义：保留 op 可反复用于形核，每次 remap 到普通 op。")
    print("      路径 A 可行且可做任意多次形核；但 remap 后该晶粒的取向会变成目标 op 的 θ，")
    print("      **这正是 per-op 取向模型的致命点**，需要路径 B/C 才能严格。")
PY
