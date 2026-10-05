#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== ① _t5_short.py 是否声明/透传 nuc-sites-refill 与 nuc-max-per-step ==="
for k in nuc-sites-refill nuc_sites_refill nuc-max-per-step nuc_max_per_step; do
  echo -n "  '$k' 出现次数 = "; grep -c "$k" _t5_short.py
done
echo "  --- 相关行原文 ---"
grep -n 'sites.refill\|sites_refill\|max.per.step\|max_per_step' _t5_short.py | cut -c1-160 | sed 's/^/    /'
echo
echo "=== ② _bk_exp.py 是否声明这两个开关 ==="
grep -n "add_argument('--nuc-sites-refill'\|add_argument('--nuc-max-per-step'" _bk_exp.py | cut -c1-160 | sed 's/^/    /'
echo
echo "=== ③ 引擎里这两个开关的默认值与作用位置 ==="
grep -n "sites_refill\|max_per_step\|sites_refilled" windowB_surface.py | head -20 | cut -c1-150 | sed 's/^/    /'
echo
echo "=== ④ R481 的 §2 起（S5 / max_per_step / 验收）==="
sed -n '60,150p' R481_NUC_SITES.md 2>/dev/null | cut -c1-160 | sed 's/^/  /'
