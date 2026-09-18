#!/bin/bash
# 数值验证 k = 1/(1 + 2*A_part/k_c)。
#
# 测三组：
#   (a) A_part=0.45, k_c=0.9  -> 公式给 k=0.500  （当前代码用的，应复现"k=0.5"的说法）
#   (b) A_part=0.264          -> 公式给 k=0.630  （Ti64 的 V，文献值）
#   (c) A_part=0.00918        -> 公式给 k=0.980  （Ti64 的 Al，文献值）
#
# 判据：数值测到的 c_solid/c_liquid 与公式值相对偏差 < 1% -> 关系式确认，C1 可据此改。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/verify_k
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
sed 's/\r$//' /mnt/f/speed_up/pipeline/verify_partition.i > base.i

# 三个变体：k_c c0 A_part
cat > variants.txt <<'EOF'
A 0.9 0.35 0.45
B 0.9 0.35 0.264
C 0.9 0.35 0.00918
EOF

while read TAG KC C0 AP; do
  mkdir -p "$TAG"
  # 【坑】sed 的 s/// 默认只替换**每行第一处**；k_c 在同一行出现两次（分子分母），
  # 不加 g 会漏掉分母那个，留下未替换的 ${k_c} 让 MOOSE 报 "no variable found"。
  sed "s/\${k_c}/$KC/g; s/\${c0}/$C0/g; s/\${A_part}/$AP/g" base.i > "$TAG/v.i"
  echo "  $TAG: k_c=$KC c0=$C0 A_part=$AP  -> 公式 k = $(python3 -c "print(f'{1/(1+2*$AP/$KC):.4f}')")"
done < variants.txt

echo
echo "=== 跑三个变体 ==="
while read TAG KC C0 AP; do
  ( cd "$TAG" && setsid --wait "$MOOSE" -i v.i > run.log 2>&1; echo "$TAG rc=$?" ) &
done < variants.txt
wait

echo
echo "================ 分配系数验证 ================"
printf "  %-4s %-10s %-10s %-12s %-12s %-10s %s\n" "变体" "A_part" "公式 k" "c_solid" "c_liquid" "实测 k" "偏差"
while read TAG KC C0 AP; do
  L="$D/$T/v_out.csv"
  if [ ! -f "$L" ]; then
    printf "  %-4s %-10s  无输出（见 $TAG/run.log）\n" "$TAG" "$AP"
    continue
  fi
  python3 - "$L" "$AP" "$KC" "$TAG" <<'PY'
import csv, sys
path, ap, kc, tag = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
rows = list(csv.DictReader(open(path)))
r = rows[-1]
cs, cl = float(r["c_solid"]), float(r["c_liquid"])
k_formula = 1.0 / (1.0 + 2.0 * ap / kc)
k_meas = cs / cl if cl != 0 else float("nan")
dev = abs(k_meas - k_formula) / k_formula * 100
flag = "  ✅" if dev < 1.0 else "  ❌ 不符！"
print(f"  {tag:<4} {ap:<10.5g} {k_formula:<10.4f} {cs:<12.6f} {cl:<12.6f} {k_meas:<10.4f} {dev:6.3f}%{flag}")
PY
done < variants.txt
echo
echo "  判据：偏差 < 1% 则关系式 k = 1/(1+2*A_part/k_c) 确认，C1 可据此把 k 改成真实值。"
