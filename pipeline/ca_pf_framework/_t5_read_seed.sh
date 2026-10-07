#!/bin/bash
# _t5_read_seed.sh --- ★★★★★ 逐行读 `seed_plate`（写入作用域 = "乙"候选的要害）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
git add pipeline/ca_pf_framework/_t5_armon.py pipeline/ca_pf_framework/_t5_frag.py \
        pipeline/ca_pf_framework/_t5_waitany.sh 2>/dev/null
git commit -m 'R581-T5R-s263b 监控脚本的本地改动（armon 加臂 / waitany 覆盖 fresh / frag 修正）' 2>&1 | tail -1
echo
echo '════ `seed_plate` 全文（2758 行起，逐行）════'
sed -n '2758,2900p' windowB_surface.py | nl -ba -v2758 | cut -c1-150
