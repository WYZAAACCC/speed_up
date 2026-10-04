#!/bin/bash
# _wsl_mem28.sh --- 把 WSL 内存上限 24GB → 28GB（保留其余行与注释编码）
F=/mnt/c/Users/mycomputer/.wslconfig
if [ ! -f "$F" ]; then echo "❌ 找不到 $F"; exit 1; fi

echo "=== 改前 ==="
grep -nE '^\[|^memory=|^processors=|^swap=|^swapFile=' "$F"

TS=$(date +%m%d_%H%M)
BAK="${F}.bak_24GB_${TS}"
cp -a "$F" "$BAK" && echo "  备份 → $(basename "$BAK")"

sed -i 's/^memory=24GB/memory=28GB/' "$F"

echo "=== 改后 ==="
grep -nE '^\[|^memory=|^processors=|^swap=|^swapFile=' "$F"
echo "=== 校验：必须恰好一处 memory=28GB ==="
echo "  memory=28GB 出现 $(grep -c '^memory=28GB' "$F") 次"
echo "  memory=24GB 残留 $(grep -c '^memory=24GB' "$F") 次"
echo "  文件字节数 = $(stat -c%s "$F")（备份 = $(stat -c%s "$BAK")）"
