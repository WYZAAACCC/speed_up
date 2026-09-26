#!/bin/bash
# 查 T5 的 A/B 两个输入到底差在哪
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
for f in stage1_meltpool_gibbs3d_t5A.i stage1_meltpool_gibbs3d_t5B.i; do
  echo "== $f"
  echo -n "   mu_barrier_gibbs = "; grep -c 'mu_barrier_gibbs' "$f"
  echo -n "   mu_barrier_const = "; grep -c 'mu_barrier_const' "$f"
  echo -n "   gamgb_name       = "; grep -c 'gamgb_name' "$f"
done
echo "== 去掉注释后的差异（前 20 行）=="
diff <(sed 's/#.*//' stage1_meltpool_gibbs3d_t5A.i | sed '/^\s*$/d') \
     <(sed 's/#.*//' stage1_meltpool_gibbs3d_t5B.i | sed '/^\s*$/d') | head -20
