#!/bin/bash
# _t5_check.sh --- 改完 `_r581_p2.py` 后的验证（打印实际命令，不跑仿真）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① 语法 ════'
$PY -m py_compile _r581_p2.py && echo '  SYNTAX_OK(真跑过)'
echo
echo '════ ② 默认档：命令里**不应**出现任何 --ckpt-* / --resume（保护归档路径）════'
$PY - <<'PYEOF'
import sys, argparse
sys.argv = ['x', '--tag', 'T', '--N', '160']
import importlib.util
spec = importlib.util.spec_from_file_location('p2', '_r581_p2.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ap = argparse.ArgumentParser()
# 直接调它的 main 不方便 ⇒ 用一个最小替身：手动复现参数解析
import types
src = open('_r581_p2.py', encoding='utf-8').read()
print('  cmd_of 里含 --ckpt 的行数 =', src.count("'--ckpt-"))
print('  cmd_of 里含 --resume 的行数 =', src.count("'--resume'"))
PYEOF
echo
echo '════ ③ 真解析一次：默认 vs 打开 ckpt，打印命令尾部 ════'
$PY - <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location('p2', '_r581_p2.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class A: pass
for tag, kw in (('默认', dict(ckpt_every=0, ckpt_keep=2, ckpt_milestone_every=0, resume='')),
                ('开ckpt', dict(ckpt_every=20, ckpt_keep=2, ckpt_milestone_every=0, resume='')),
                ('续跑', dict(ckpt_every=20, ckpt_keep=2, ckpt_milestone_every=0,
                            resume='_exp/_bk_p5/dry_p5/ckpt'))):
    a = A()
    for k, v in dict(N=160, steps=40, nthreads=4, m=4, B=5, out='_exp/_bk_p5', tag='p5',
                     overlap_nm=62.5, periodic_seed=1, ckpt_every=0, ckpt_keep=2,
                     ckpt_milestone_every=0, resume='').items():
        setattr(a, k, v)
    for k, v in kw.items():
        setattr(a, k, v)
    c = m.cmd_of(a)
    tail = [x for i, x in enumerate(c) if x.startswith('--ckpt') or x.startswith('--resume')]
    print('  %-6s ⇒ %s' % (tag, tail if tail else '（无 ckpt 参数 ⇒ 归档路径不变 ✓）'))
    nsw = sum(1 for x in c if x.startswith('--'))
    print('           开关总数 = %d' % nsw)
PYEOF
