#!/bin/bash
cd /root/moose/modules/phase_field/test/tests/grain_growth || exit 1

echo "===== 该目录下所有 .i 文件 ====="
ls -la *.i

echo
echo "===== 哪个 .i 对应 temperature_gradient ====="
grep -ln 'temperature_gradient' *  2>/dev/null
grep -rn 'temperature_gradient' . --include='tests' -A4 2>/dev/null | head -30

echo
echo "===== temperature_gradient 相关输入文件全文 ====="
for f in $(grep -rln 'temperature\|gradient' *.i 2>/dev/null); do
    echo "########## $f ##########"
    cat "$f"
    echo
done

echo
echo "===== columnar 相关 ====="
grep -rln 'columnar' . 2>/dev/null | head
