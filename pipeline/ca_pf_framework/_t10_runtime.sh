#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10PRT2_b3_1005_1213.log
[ -f "$L" ] || L=_w2_t5_short_t10B9.log
echo "=== $L （总行数 $(wc -l < "$L")）==="
echo
echo "── ① wrap / 绕盒 / check_wrap 的运行期输出 ──"
grep -anE 'wrap|绕盒|贯通|percolat' "$L" 2>/dev/null | head -12 | tr -d '\r' | cut -c1-160 | sed 's/^/  /'
echo "  （命中数 = $(grep -acE 'wrap|绕盒|贯通' "$L" 2>/dev/null)）"
echo
echo "── ② reinit / 重初始化 ──"
grep -anE 'reinit|重初始' "$L" 2>/dev/null | head -8 | tr -d '\r' | cut -c1-160 | sed 's/^/  /'
echo "  （命中数 = $(grep -acE 'reinit|重初始' "$L" 2>/dev/null)）"
echo
echo "── ③ 看门狗 / 内存 / 收敛 ──"
grep -anE '看门狗|watchdog|收敛|relax|VmRSS|MB' "$L" 2>/dev/null | head -10 | tr -d '\r' | cut -c1-160 | sed 's/^/  /'
echo
echo "── ④ 步进行（全部；含 nsig/nf3col/nc/包围跨度）──"
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tr -d '\r' | cut -c1-175 | sed 's/^/  /'
echo
echo "── ⑤ 自检类（S-1..S-9 / P-x / R-4 / M-x）──"
grep -anE 'S-[0-9]|P-[0-9]|R-[0-9]|M-[0-9]|自检|判据|FAIL|PASS' "$L" 2>/dev/null | head -20 | tr -d '\r' | cut -c1-160 | sed 's/^/  /'
echo
echo "── ⑥ 末 25 行（真实结尾）──"
tail -25 "$L" 2>/dev/null | tr -d '\r' | cut -c1-160 | sed 's/^/  /'
