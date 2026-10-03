#!/bin/bash
# _t5_nfsvA.sh --- 步骤 A：查 `nfsv` 的实现与 `T_events` 记的到底是哪个场
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `nfsv` 在 windowB_surface.py 里的全部出现（行号 + 内容）════'
grep -n "nfsv" windowB_surface.py 2>/dev/null | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② `T_events` 是在哪里被记的（找 n_events / T_events 的写入点）════'
grep -n "T_events\|'field':\|nfsv_ok\|nfsv_nofield\|d\['field'\]" windowB_surface.py 2>/dev/null | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ③ `dbg` 里所有计数键（看有没有 nofield 类）════'
grep -n "dbg\[" windowB_surface.py 2>/dev/null | cut -c1-140 | sed 's/^/  /' | head -30
