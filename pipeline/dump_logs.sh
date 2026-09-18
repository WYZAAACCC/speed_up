#!/bin/bash
# 转储关键日志片段，用于诊断当前卡点

echo "########## 1. multi/run1 报错段 ##########"
grep -n -i -B3 -A12 'error\|ERROR\|terminate\|abort\|FAQ page' /root/work/multi/run1/run.log | tail -60

echo
echo "########## 2. multi/run1 最后 30 行 ##########"
tail -30 /root/work/multi/run1/run.log

echo
echo "########## 3. multi2/run1 最后 15 行 ##########"
tail -15 /root/work/multi2/run1/run.log

echo
echo "########## 4. roll2.log 全文 ##########"
cat /root/work/roll2.log

echo
echo "########## 5. roll3.log 全文 ##########"
cat /root/work/roll3.log

echo
echo "########## 6. tcmp.log 全文 ##########"
cat /root/work/tcmp.log

echo
echo "########## 7. 其它日志文件 ##########"
ls -la /root/work/*.log /root/work/logs/ 2>/dev/null
