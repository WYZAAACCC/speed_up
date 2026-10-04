#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== nuc_sites_refill / nuc_init 的接线（引擎 + 透传）==="
grep -n 'sites_refill\|sites_margin\|nuc_sites' _bk_exp.py _t5_short.py windowB_surface.py | cut -c1-170
echo
echo "=== sites 池的初始化 / 生成 / pop ==="
grep -n "'sites'\|sites\.pop\|c\['sites'\]\|_nuc_place_initial" windowB_surface.py | cut -c1-170
echo
echo "=== sites_refill 生效的日志证据（构造横幅里有没有）==="
grep -a 'sites' _w2_t5_short_t5ETAo.log | head -6 | cut -c1-170
