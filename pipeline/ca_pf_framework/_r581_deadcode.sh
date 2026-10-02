#!/bin/bash
# _r581_deadcode.sh --- ★ 自己核实（不引用注释）：`_nuc_safe_mask()` 到底有没有被调用？
cd "$(dirname "$0")" || exit 1
echo '=== `_nuc_safe_mask` 在主副本里的每一处出现（定义 + 调用）==='
grep -n '_nuc_safe_mask' windowB_surface.py | sed 's/^/  /'
echo
echo '=== 统计 ==='
def=$(grep -c 'def _nuc_safe_mask' windowB_surface.py)
all=$(grep -c '_nuc_safe_mask' windowB_surface.py)
echo "  出现总数 = $all ；其中定义 = $def ⇒ **调用/引用 = $((all - def))**"
echo
echo '=== 全仓（含所有 .py）里谁调它 ==='
grep -rn '_nuc_safe_mask' --include='*.py' . 2>/dev/null | grep -v '_r580_backup' | grep -v 'def _nuc_safe_mask' | sed 's/^/  /'
echo '  （空 = 主副本里零调用）'
echo
echo '=== `nfsv_nofield` 在主副本里的每一处 ==='
grep -n 'nfsv_nofield' windowB_surface.py | sed 's/^/  /'
