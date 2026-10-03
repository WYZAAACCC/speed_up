#!/bin/bash
# _t5_engelong.sh --- ★★★★★ 查 `--eng-elong`：默认值 / 启动器传了什么 / 横幅打印了什么
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① CLI 定义与**默认值** ════'
grep -n "add_argument('--eng-elong'" _bk_exp.py | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ② 1900-1912 那段的**原文**（它决定打印"长条"还是别的）════'
sed -n '1900,1914p' _bk_exp.py | sed 's/^/  /'
echo
echo '════ ③ 我的启动器有没有传 `--eng-elong` ════'
grep -n "eng-elong\|eng_elong" _t5_short.py | cut -c1-140 | sed 's/^/  /'
echo '  （空 = 没传 ⇒ 用引擎默认）'
echo
echo '════ ④ ★ 运行横幅里实际打印的那一行 ════'
for t in t5H3 t5V2; do
  echo "  ── $t ──"
  grep -nE '长条|各向同性|eng-elong|elong=' _w2_t5_short_$t.log 2>/dev/null | head -4 | cut -c1-150 | sed 's/^/     /'
done
echo
echo '════ ⑤ 该参数在别处的用法（看它是否只在"引擎路径"生效）════'
grep -n "eng_elong" _bk_exp.py | cut -c1-150 | sed 's/^/  /'
