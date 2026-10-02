#!/bin/bash
# _t5_nofield.sh --- 读 `nfsv_nofield` 分支的**上下文**（引擎自己写明了原因）
cd "$(dirname "$0")" || exit 1
echo '════ windowB_surface.py:2320-2345（nfsv_nofield 的判定与自陈）════'
sed -n '2318,2348p' windowB_surface.py | cat -n | cut -c1-130 | sed 's/^/  /'
echo
echo '════ :2385-2400（nfsv_strict 的分支）════'
sed -n '2385,2400p' windowB_surface.py | cat -n | cut -c1-130 | sed 's/^/  /'
echo
echo '════ :1665-1680（另一处 nfsv_nofield 的说明）════'
sed -n '1663,1682p' windowB_surface.py | cat -n | cut -c1-130 | sed 's/^/  /'
