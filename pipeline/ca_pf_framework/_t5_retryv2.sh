#!/bin/bash
# _t5_retryv2.sh --- 验证 argparse + 重跑 V2 启动
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① 语法与参数定义 ════'
$PY -m py_compile _t5_short.py && echo '  ✅ SYNTAX_OK'
echo
echo '════ ② ★ argparse 真解析一次（**判据**：能接受 --var-rule random / --nuc-fresh-every 5）════'
$PY - <<'PYEOF'
import subprocess, sys, os
# 用 `--help` 触发 argparse 构建（不启动引擎）；再看两个参数在不在 help 里
r = subprocess.run([sys.executable, '_t5_short.py', '--help'],
                   capture_output=True, text=True, cwd='.')
h = r.stdout + r.stderr
print('  --help 退出码 =', r.returncode, '（0 = argparse 构建成功）')
for k in ('--var-rule', '--nuc-fresh-every', '--therm-hist'):
    print('    help 里含 %-20s = %s' % (k, k in h))
PYEOF
echo
echo '════ ③ 长跑仍在（未受影响）════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
free -m | sed -n 2p | sed 's/^/  /'
