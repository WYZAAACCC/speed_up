#!/bin/bash
# 量化 op_num 提升对 aniso_block.i 规模的影响（B2 与形核路径 A 的权衡依据）。
#
# 背景：
#   * B0a 实测 reserve_op 是【永久槽位】=> op_num 必须 >= 基体晶粒数 + 期望形核次数
#   * 但 L2a 的取向差对是 O(n^2)，8 个 op 已展开成 ~2400 字符的解析式
#   * 且 MOOSE_AD_MAX_DOFS_PER_ELEM=64 给出硬上限：op_num > 13 就不能走 AD
# 本脚本只做**离线规模统计**，不跑 MOOSE，不占 CPU。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
cd /root/work || exit 1
mkdir -p opcost && cd opcost || exit 1
cp /mnt/f/speed_up/pipeline/gen_aniso.py .
cp /mnt/f/speed_up/pipeline/splice_aniso.py .
cp /root/work/s1d_w/stage1_meltpool_c.i . 2>/dev/null || cp /mnt/f/speed_up/pipeline/stage1_meltpool_c.i .
cp /mnt/f/speed_up/pipeline/columnar_seeds.csv . 2>/dev/null

echo "  op_num |  块大小 | L2a 长度 | 最大表达式 | 变量数 | AD 可行?"
echo "  -------+---------+----------+------------+--------+---------"
for N in 8 11 13 14 16; do
  python3 gen_aniso.py --op-num $N --out "blk_$N.i" > /dev/null 2>&1 || { echo "  $N gen 失败"; continue; }
  [ -f "blk_$N.i" ] || { echo "  $N 无输出"; continue; }
  SZ=$(stat -c%s "blk_$N.i")
  # 抽出 L2a 的 expression 行长度
  L2A=$(grep -A30 'property_name = L2a' "blk_$N.i" | grep -m1 'expression' | wc -c)
  # 全文件最长的一行
  MAXL=$(awk '{ if (length($0) > m) m = length($0) } END { print m }' "blk_$N.i")
  NVAR=$((N + 3))
  DOF=$((NVAR * 4))
  if [ "$DOF" -le 64 ]; then AD="是 ($DOF<=64)"; else AD="**否** ($DOF>64)"; fi
  printf "  %6s | %7s | %8s | %10s | %6s | %s\n" "$N" "$SZ" "$L2A" "$MAXL" "$NVAR" "$AD"
done

echo
echo "  注：'变量数' = op_num + 3（c, w, T）；QUAD4 每单元 4 节点。"
echo "      MOOSE_AD_MAX_DOFS_PER_ELEM = 64 是**编译期常量**，超了必须重编译 MOOSE。"
echo
echo "  对照（ROADMAP §三）：8 个 op 时 L2a 有 28 对；16 个 op 有 120 对。"
