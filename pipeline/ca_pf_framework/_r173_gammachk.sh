#!/bin/bash
# _r173_gammachk.sh —— `§129` 影响面排查：**哪些算例真的用了 `gamma0 = 0.15`？**
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python

echo "=== ① 有 .sh 传 --gamma0 启动器的个数 ==="
N=$(grep -h -- '--gamma0' ./*.sh 2>/dev/null | wc -l)
echo "    命中行数 = $N"
grep -h -- '--gamma0' ./*.sh 2>/dev/null | sed 's/^[[:space:]]*/    /' | head -20

echo
echo "=== ② 闭环主情景的 F1 面能常数（R29 引入）==="
grep -rn 'GAMMA_F1_MAIN\|GAMMA_F1_BAND' ./*.py | head -12

echo
echo "=== ③ 归档算例逐个查 meta.json 里的 gamma0 / laths ==="
for d in dry_mb2fp10 dry_mb2fp0 dry_mo1fp10 dry_saSet2 dry_saOddG \
         dry_saSet2F2 dry_saOddGF2 dry_swapinv dry_swN128 dry_t1N112L800 \
         dry_t3N128L1000 dry_sgG dry_cl1; do
  f="_exp/_bk_mb/$d/meta.json"
  if [ -f "$f" ]; then
    printf '    %-16s ' "$d"
    $PY -c 'import json,sys
m=json.load(open(sys.argv[1]))
ks=("gamma0","laths","f2_lam","f2_pair_gamma","rank1_swap","facet_proj","N","plate_L_nm")
print("  ".join("%s=%s"%(k,m[k]) for k in ks if k in m))' "$f"
  else
    printf '    %-16s (无 meta.json)\n' "$d"
  fi
done

echo
echo "=== ④ 归档算例第 1 行有没有直接记 gamma（series.csv 表头）==="
for d in dry_mb2fp10 dry_saSet2; do
  f="_exp/_bk_mb/$d/series.csv"
  [ -f "$f" ] && { printf '    %-16s ' "$d"; head -1 "$f" | tr ',' '\n' | grep -i -n 'gam\|n_f3\|n_f2' | tr '\n' ' '; echo; }
done

echo
echo "=== ⑤ 全部归档臂里出现过的 --laths 组合（去重计数）==="
grep -ho -- '--laths [0-9,]*' ./*.sh 2>/dev/null | sed 's/--laths //' | sort | uniq -c | sort -rn | head -20
