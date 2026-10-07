#!/bin/bash
# _t5_compchk.sh --- ★★★★★ `t5N276F` 有没有开 `--nuc-compensate`？（代码注释说它是"碎裂"的解药）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 引擎实际收到的相关参数（从 /proc 读，最可靠）════'
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5N276F' | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  tr '\0' '\n' < /proc/$P/cmdline 2>/dev/null | grep -iE 'compensate|overlap|gap|seed|nuc' | sed 's/^/  /'
else
  echo '  （引擎进程不在，改查启动脚本与默认值）'
fi
echo
echo '════ ② 启动脚本里有没有传 ════'
grep -nE 'compensate' _t5_nv276F.sh _t5_nv276.sh _t5_short.py 2>/dev/null | cut -c1-150 | sed 's/^/  /'
echo '  ⇒ 若上面为空 ⇒ **都没传** ⇒ 用默认值'
echo
echo '════ ③ `--nuc-compensate` 的**默认值** ════'
grep -nE "add_argument\('--nuc-compensate" _bk_exp.py | cut -c1-165 | sed 's/^/  /'
grep -nE "add_argument\('--nuc-compensate-frac" _bk_exp.py | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ④ 参数真正生效的地方（三处读取点）════'
grep -nE "nuc_compensate" _bk_exp.py | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ⑤ 大算例横幅里有没有提到它 ════'
grep -nE 'compensate|补厚|预补' _w2_t5_short_t5N276F.log 2>/dev/null | head -6 | cut -c1-160 | sed 's/^/  /'
echo '  ⇒ 若为空 ⇒ **横幅没报它** ⇒ 需要从 argv/默认值判'
