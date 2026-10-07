#!/bin/bash
# _r576_check.sh --- R576：钩子接入后的**语法 + 导入 + 钩子自证**三步快检。
# 判据（任一不过即停）：
#   C1 三个文件 py_compile 通过
#   C2 `import windowB_surface` 通过（含 windowB_acct / windowB_par / windowB_pf3d）
#   C3 关闭钩子时 `acct.mark` 返回单例 `_NOOP`（零分配路径真的走了）
#   C4 打开钩子后 `with acct.mark('x')` 能计时、能计数
#   C5 `span_begin/span_end` 的**配对自检**有效：故意只 begin 不 end ⇒ corrupt() 非空
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== R576 CHECK $(date '+%F %T')  host=$(hostname) ==="
$PY - <<'PYEOF'
import sys, os
sys.path.insert(0, os.getcwd())
import py_compile
bad = 0
for f in ('windowB_acct.py', 'windowB_par.py', 'windowB_pf3d.py', 'windowB_surface.py'):
    try:
        py_compile.compile(f, doraise=True)
        print('  C1 %-22s py_compile OK' % f)
    except Exception as e:
        print('  C1 %-22s FAIL %r' % (f, e)); bad = 1
import windowB_acct as acct
import windowB_surface as W
import windowB_par as PAR
import windowB_pf3d as P3
print('  C2 import OK   (numpy %s)' % __import__('numpy').__version__)

# C3 关闭时零分配路径
assert not acct.enabled()
a = acct.mark('t'); b = acct.mark('t')
print('  C3 关闭时 mark() 返回单例: %s' % ('OK' if a is b and a is acct._NOOP else 'FAIL'))
if not (a is b and a is acct._NOOP):
    bad = 1

# C4 打开后能计时/计数
acct.enable()
acct.reset()
with acct.mark('t4'):
    s = 0
    for i in range(200000):
        s += i
T, C = acct.totals()
ok = (C.get('t4') == 1 and T.get('t4', 0) > 0)
print('  C4 打开后 mark(): count=%s time=%.6f s ⇒ %s'
      % (C.get('t4'), T.get('t4', 0), 'OK' if ok else 'FAIL'))
if not ok:
    bad = 1

# C5 配对自检
acct.reset()
acct.span_begin('t5')
c = acct.corrupt()
print('  C5 span 配对自检: 缺 span_end ⇒ corrupt=%r ⇒ %s'
      % (c, 'OK（能看见）' if c else 'FAIL（静默）'))
if not c:
    bad = 1
acct.reset()
acct.span_begin('t5'); acct.span_end('t5')
c = acct.corrupt()
T, C = acct.totals()
print('  C5b 正常配对 ⇒ corrupt=%r, count=%s ⇒ %s'
      % (c, C.get('t5'), 'OK' if (not c and C.get('t5') == 1) else 'FAIL'))
if c or C.get('t5') != 1:
    bad = 1
acct.disable()
print('  === RESULT: %s ===' % ('ALL PASS' if bad == 0 else 'FAIL'))
sys.exit(bad)
PYEOF
echo "=== R576 CHECK DONE rc=$? $(date '+%F %T') ==="
