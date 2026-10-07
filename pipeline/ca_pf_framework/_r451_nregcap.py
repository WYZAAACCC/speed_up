#!/usr/bin/env python3
"""_r451_nregcap.py —— ★★ **`nreg ≤ 127` 这个上限到底卡在哪、改起来多大？**

回答用户的问题：「位置数能否通过修改程序增多?」

做法：把仓库里**所有**跟 `nreg`/`region` 的整数类型有关的地方找出来，
并实测"当前每步耗时 / 内存"随场数的关系。
"""
import os
import re
import subprocess
import sys

P = print
ROOT = '.'
P('=' * 92)
P('_r451 —— `nreg` 上限的**真实范围**')
P('=' * 92)

# ---------------------------------------------------------------- 1) int8 出现处
P('\n[1] 全仓 `int8` 出现处（`*.py`，排除日志/数据目录）')
pat = re.compile(r'int8')
hits = []
for fn in sorted(os.listdir(ROOT)):
    if not fn.endswith('.py'):
        continue
    try:
        for i, ln in enumerate(open(fn, encoding='utf-8', errors='replace'), 1):
            if pat.search(ln) and not ln.lstrip().startswith('#'):
                hits.append((fn, i, ln.rstrip()[:110]))
    except OSError:
        pass
for fn, i, ln in hits:
    P('    %-24s :%-5d %s' % (fn, i, ln))

# ---------------------------------------------------------------- 2) nreg 的守卫
P('\n[2] 与 `nreg` 上限有关的守卫 / 报错')
guard = []
for fn in sorted(os.listdir(ROOT)):
    if not fn.endswith('.py'):
        continue
    try:
        for i, ln in enumerate(open(fn, encoding='utf-8', errors='replace'), 1):
            if ('超过' in ln and 'int8' in ln) or ('nreg' in ln and 'raise' in ln):
                guard.append((fn, i, ln.rstrip()[:110]))
    except OSError:
        pass
for fn, i, ln in guard:
    P('    %-24s :%-5d %s' % (fn, i, ln))
if not guard:
    P('    （没有硬守卫；上限是**隐式**的：`astype(np.int8)` 溢出后静默回绕）')

# ---------------------------------------------------------------- 3) 实测成本
P('\n[3] 实测：s/步 与 内存 随场数（从**正在跑**的两条臂的日志与进程读）')
for tag, lg in (('abA', '_r445_abA.log'), ('abB', '_r445_abB.log')):
    if not os.path.exists(lg):
        continue
    txt = open(lg, encoding='utf-8', errors='replace').read()
    sp = re.findall(r'([0-9]+\.[0-9]+)s/步', txt)
    P('    %s：s/步 采样 %d 个，末 3 个 = %s' % (tag, len(sp), sp[-3:]))
try:
    out = subprocess.run(['ps', '-eo', 'rss=,args='], capture_output=True,
                         text=True).stdout
    for ln in out.splitlines():
        if '--tag ab' in ln:
            parts = ln.split(None, 1)
            P('    进程 RSS = %.2f GB  （%s）'
              % (int(parts[0]) / 1048576.0, parts[1][:60]))
except Exception as e:
    P('    （进程读取失败：%r）' % e)

# ---------------------------------------------------------------- 4) 结论
P('\n' + '=' * 92)
P('[结论]')
P('  **只有 2 行**真正把上限钉在 127：`windowB_surface.py:1226/1227`')
P('      return np.argmin(self.phi, axis=0).astype(np.int8)')
P('  其余 `int8` 都在**合成测试夹具**（`_bk_measure` 的自检）与**快照的 band 字段**里。')
P('  ⇒ 改成 `np.int16` 上限变 **32767**；改成 `np.int32` 基本等于无限。')
P('  代价（**待实测**）：`region` 数组本身极小（1.4 M 胞 × 2 B = 2.8 MB），')
P('  真正吃内存/时间的是 `phi`（(nreg+1, N,N,N)）与 FFT。')
P('=' * 92)
