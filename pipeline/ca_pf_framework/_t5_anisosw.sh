#!/bin/bash
# _t5_anisosw.sh --- 找 `aniso_elastic` 的 CLI 开关与传参链
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `aniso_elastic` 在 `_bk_exp.py` 里的出现处 ════'
grep -n 'aniso_elastic' _bk_exp.py 2>/dev/null | head -14 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② 现成的 CLI 参数（add_argument 里含 aniso 的）════'
grep -nE 'add_argument.*aniso' _bk_exp.py 2>/dev/null | cut -c1-170 | sed 's/^/  /'
echo '  ⇒ 若为空 ⇒ **没有现成开关** ⇒ 需加透传'
echo
echo '════ ③ `LevelSetMulti` 里 `aniso_elastic` 的入参名与默认 ════'
grep -n 'aniso_elastic' windowB_surface.py 2>/dev/null | head -8 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ④ 引擎 argv 里实际有没有（在跑的臂）════'
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  tr '\0' '\n' < /proc/$P/cmdline 2>/dev/null | grep -i 'aniso' | sed 's/^/  /'
  echo "  （进程 pid=$P；若上面为空 ⇒ 未开各向异性弹性）"
else
  echo '  （无引擎进程）'
fi
