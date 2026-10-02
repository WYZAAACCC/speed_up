#!/bin/bash
# _r581_docsize.sh --- 查 AGENTS.md 是否仍在工作区指令预算内
cd /mnt/f/speed_up || exit 1
SZ=$(stat -c%s AGENTS.md)
echo "AGENTS.md = $SZ 字节（预算 65536）"
if [ "$SZ" -lt 65536 ]; then
  echo "  ✅ 仍在预算内；余量 $((65536 - SZ)) 字节"
else
  echo "  ❌ **超预算 $((SZ - 65536)) 字节** ⇒ 会被截断 ⇒ 必须继续搬正文"
fi
echo
echo '── 新增段落是否就位 ──'
grep -c 'P49' AGENTS.md | sed 's/^/  P49 出现次数：/'
grep -n '§7.5 续二' AGENTS.md | head -2 | sed 's/^/  /'
