#!/bin/bash
# _r581_gate1_smoke.sh --- 冒烟 + 逐位比较（一条命令跑完，避免引号地狱）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '── ① 语法 ──'
$PY -m py_compile _bk_exp.py && echo '   SYNTAX_OK（真跑过）'
echo
echo '── ② 重跑冒烟（S1 存 / S2 续跑 / S3 连续对照）──'
timeout 2400 bash _r581_resume_smoke.sh > /dev/null 2>&1
echo "   冒烟 exit=$?"
grep -E '从检查点续跑|自动选|检查点 step=|P0 已回填|驱动层已回填|版本哈希' \
  _w2_r581_rsmoke_rs2.log 2>/dev/null | tail -8 | sed 's/^/   /'
echo
echo '── ③ 结果表 ──'
for t in rs1 rs2 rs3; do
  printf '   %-4s 行数=%-4s 末步=%s\n' "$t" \
    "$(wc -l < "_exp/_bk_rsmoke/dry_$t/series.csv" 2>/dev/null)" \
    "$(tail -1 "_exp/_bk_rsmoke/dry_$t/series.csv" 2>/dev/null | cut -d, -f1)"
done
echo
echo '── ④ ★ 逐位比较（S2 续跑 vs S3 连续）──'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  _exp/_bk_rsmoke/dry_rs2/series.csv _exp/_bk_rsmoke/dry_rs3/series.csv step
echo
echo '── ⑤ 顺带验证：resume 的**非法值硬失败**（判据⑥）──'
$PY -u _bk_exp.py --N 64 --steps 8 --resume _exp/_bk_rsmoke/dry_rs1/ckpt \
  --out _exp/_bk_rsmoke --tag rsbad --laths 1 2>&1 | tail -3 | sed 's/^/   /'
