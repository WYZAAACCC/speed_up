#!/bin/bash
# 看二维停滞时最后几个"变量级残差 + 最大残差位置"
set +u
L=/root/work/g3d2d_dbg/run.log
sed 's/\x1b\[[0-9;]*m//g' "$L" > /tmp/d2.txt
echo "dump 次数 = $(grep -c 'residual|_2 of individual' /tmp/d2.txt)"
echo "=== 最后一次失败步之前的 3 个 dump 的变量级残差 ==="
awk '/residual\|_2 of individual/{n++; buf=""; grab=1; next}
     grab && /gr0:|c:  |w:  |Gam/{buf=buf"\n"$0; next}
     grab && /^$/{if(buf!=""){last[++k]=buf; grab=0}; next}
     END{for(i=k-2;i<=k;i++) if(i>0) print "---- dump " i " ----" last[i]}' /tmp/d2.txt | tail -40
echo "=== 最后一次 [DBG] 最大残差位置 ==="
grep -n 'DBG' /tmp/d2.txt | tail -8
