#!/bin/bash
# _t5_eps0chk.sh --- ★★★★★★ 读模型的**真实 ε⁰** 与 `aniso_elastic` 开关
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① ε⁰ 的定义处（找数值，不是引用）════'
grep -nE 'eps0 *=|EPS0 *=|e0 *=|eps0_list|self\.eps0' windowB_pf3d.py windowB_km.py windowB_surface.py 2>/dev/null \
  | grep -vE '^\s*#' | head -18 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② 数值附近的上下文（含数字的行）════'
for F in windowB_pf3d.py windowB_km.py; do
  L=$(grep -nE 'eps0 *=|EPS0 *=' "$F" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -n "$L" ]; then
    echo "  ── $F 第 $L 行起 ──"
    sed -n "$((L-8)),$((L+14))p" "$F" | nl -ba -v$((L-8)) | cut -c1-150 | sed 's/^/    /'
    break
  fi
done
echo
echo '════ ③ `aniso_elastic` 的默认值与赋值 ════'
grep -nE 'aniso_elastic' windowB_surface.py _bk_exp.py 2>/dev/null | head -10 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ④ 引擎 argv 里有没有开各向异性弹性/相关开关 ════'
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  tr '\0' '\n' < /proc/$P/cmdline 2>/dev/null | grep -iE 'aniso|elas|eps0|C11|C12|C44|strain' | sed 's/^/  /'
else
  grep -oE "'--[a-z-]*(aniso|elas|eps0)[a-z-]*', *'?[0-9a-zA-Z.]*'?" _t5_short.py | sed 's/^/  /'
fi
echo '  ⇒ 若上面为空 ⇒ **没有显式开关** ⇒ 用类属性默认值'
