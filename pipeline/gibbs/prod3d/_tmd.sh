#!/bin/bash
set +u
cd /root/work/maxder || exit 1
sed -i 's|property = "d2f_loc/dc2"|property = "d^2f_loc/dc^2"|' case.i
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
echo "FREF=1.6423e9  CFLOOR=1e-6   ???: FREF*( max(c,CF)*log(max(c,CF)) )"
printf "%-9s %-16s %-16s %-16s\n" "c" "f_loc" "df_loc/dc" "d^2f_loc/dc^2"
for v in 0.036 0.001 0.0 -0.01 -0.1; do
  iso="0.036"; [ "$v" = "0.0" ] && iso="0"
  /root/projects/gibbs/gibbs-opt -i case.i ICs/c_ic/value=$v Outputs/file_base=out_x > log_x.txt 2>&1
  line=$(tail -1 out_x.csv 2>/dev/null)
  python3 -c "
import sys
s='''$line'''.strip().split(',')
print('%-9s %-16s %-16s %-16s'%('$v', s[1] if len(s)>1 else 'ERR', s[2] if len(s)>2 else '', s[3] if len(s)>3 else ''))
"
done
echo "=== ???? df/dc = 1.6423e9*(ln(c)+1) , d2f/dc2 = 1.6423e9/c ==="
python3 -c "
import math
F=1.6423e9; CF=1e-6
for c in [0.036,0.001,0.0,-0.01,-0.1]:
    cc=max(c,CF)
    f=F*cc*math.log(cc); df=F*(math.log(cc)+1); d2=F/cc
    print('%-9s %-16.6g %-16.6g %-16.6g'%(c,f,df,d2))
"
