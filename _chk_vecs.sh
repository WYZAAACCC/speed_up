#!/bin/bash
F=/mnt/f/speed_up/bench/exaca/GrainOrientationVectors.csv
head -3 $F
echo "=== 每行列数:"; awk -F, 'NR<=3{print NR": "NF" 列"}' $F
echo "=== 总行数:"; wc -l $F
echo "=== 第 2 行的前 3 个数的模:"; awk -F, 'NR==2{print sqrt($1*$1+$2*$2+$3*$3), sqrt($4*$4+$5*$5+$6*$6), sqrt($7*$7+$8*$8+$9*$9)}' $F