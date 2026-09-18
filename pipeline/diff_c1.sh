#!/bin/bash
# 对比 c1.i（新参数，跑不动）与 bench_asm 用的旧配置（跑得动），
# 找出**除 c0/A_part 之外**是否还有意外差异。
echo "############ 1. c1.i vs bench_asm.i（只应差 c0/A_part 与输出/终点）############"
diff <(grep -vE '^\s*#|^\s*$' /root/work/c1/run/c1.i) \
     <(grep -vE '^\s*#|^\s*$' /root/work/bench_full_asm/bench_asm.i) | head -40

echo
echo "############ 2. 两者 f_loc 材料 ############"
echo "--- c1.i ---"
grep -A6 'constant_names' /root/work/c1/run/c1.i | head -10
echo "--- bench_asm.i ---"
grep -A6 'constant_names' /root/work/bench_full_asm/bench_asm.i | head -10

echo
echo "############ 3. 两者 IC ############"
echo "--- c1.i ---"
grep -B1 -A4 '\[c_init\]' /root/work/c1/run/c1.i
echo "--- bench_asm.i ---"
grep -B1 -A4 '\[c_init\]' /root/work/bench_full_asm/bench_asm.i
