#!/bin/bash
cd /mnt/f/speed_up
echo "=== 文献清单文件:"
ls docs/ 2>/dev/null | head -20
echo; echo "=== LIT_SEARCH_BRIEF 里的【仿真】类条目:"
grep -n -i 'simulat\|CA\|phase.field\|Monte\|kinetic Monte\|ExaCA\|cellular automata' docs/LIT_SEARCH_BRIEF_Ti64_LPBF.md 2>/dev/null | head -30
echo; echo "=== 该文件里的 L 编号条目（前 40 行）:"
head -40 docs/LIT_SEARCH_BRIEF_Ti64_LPBF.md 2>/dev/null