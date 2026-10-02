#!/bin/bash
# _r581_docprep.sh --- 文档固化前的准备：查 AGENTS.md 体积 + 找插入点
cd /mnt/f/speed_up || exit 1
SZ=$(stat -c%s AGENTS.md)
echo "AGENTS.md 字节数 = $SZ（工作区指令预算 65536）"
echo "  余量 = $((65536 - SZ)) 字节"
echo "  ⇒ 若余量 < 4000 ⇒ **只能加极简一行式摘要**（正文放 R581_DISCIPLINES.md）"
echo
echo '── §7.5 续（P15–P31 摘要表）的结尾 ──'
grep -n 'P31' AGENTS.md | head -4 | cut -c1-118
echo
echo '── 该表最后一行之后是什么 ──'
LAST=$(grep -n '^\*\*P31\*\*' AGENTS.md | head -1 | cut -d: -f1)
[ -z "$LAST" ] && LAST=$(grep -n 'P31' AGENTS.md | head -1 | cut -d: -f1)
echo "  （P31 行号 = ${LAST:-未找到}）"
sed -n "$((LAST)),$((LAST+6))p" AGENTS.md 2>/dev/null | cut -c1-118
