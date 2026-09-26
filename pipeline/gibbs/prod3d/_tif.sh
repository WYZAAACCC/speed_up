#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work || exit 1
rm -rf iftest; mkdir -p iftest; cd iftest
sed "s/\r$//" /mnt/f/speed_up/pipeline/gibbs/prod3d/_test_if.i > case.i
echo "???: if(c<C1, AA*(c-C1)+BB, c*log(c))   C1=1e-3 AA=7 BB=-0.00790679"
echo "??: time, ddv(d^2), dv(d), vv(f)  <- MOOSE CSV ?????"
printf "%-8s %-14s %-14s %-14s %s\n" "c" "f" "df/dc" "d2f/dc2" "??"
for v in 0.036 0.01 0.001 5e-4 0.0 -0.01 -0.1; do
  /root/projects/gibbs/gibbs-opt -i case.i ICs/c_ic/value=$v Outputs/file_base=o > lg.txt 2>&1
  line=$(tail -1 o.csv 2>/dev/null)
  printf "%-8s %s\n" "$v" "$line"
  grep -m1 -E "\*\*\* ERROR" lg.txt
done
echo "--- ?? ---"
python3 -c "
import math
C1=1e-3;AA=7.0;BB=-0.00790679
for c in [0.036,0.01,0.001,5e-4,0.0,-0.01,-0.1]:
    if c<C1: f=AA*(c-C1)+BB; d=AA; d2=0.0
    else: f=c*math.log(c); d=math.log(c)+1; d2=1.0/c
    print('%-8s %-14.6g %-14.6g %-14.6g'%(c,f,d,d2))
"
