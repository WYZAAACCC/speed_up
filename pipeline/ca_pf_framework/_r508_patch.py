#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r508_patch.py —— 把 `shape` 参数从 `nuc_cfg` 一路接到 `seed_plate` 的**四处**调用点。

（本文件是一次性的补丁工具；改完即弃，不进回归。改动全部是**可选参数**，
 默认 `'disc'` ⇒ 归档路径逐位不变。）
"""
import io
import sys

P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
n0 = len(s)
cnt = []


def rep(old, new, tag):
    global s
    if old not in s:
        print('  ❌ 找不到：%s' % tag)
        return False
    s = s.replace(old, new, 1)
    cnt.append(tag)
    return True


# ① 超临界探针签名 + 内部 seed_plate
rep("def _supercrit_probe(self, kk, cc, nrm, R, t, cover, df, gamma):",
    "def _supercrit_probe(self, kk, cc, nrm, R, t, cover, df, gamma,\n"
    "                          shape='disc'):",
    '探针签名')

rep("            self.seed_plate(kk, cc, nrm, R, t, undo=bak)",
    "            self.seed_plate(kk, cc, nrm, R, t, undo=bak, shape=shape)",
    '探针内 seed_plate')

# ② fresh 通道：把 shape 传进去（并把它传给探针）
rep("""                            self.seed_plate(kk, _cc, _nrm, R, t,
                                            elong=(c.get('elong', 1.0)
                                                   if c.get('along_per_variant')
                                                   else 1.0),
                                            along=_along_of(kk),
                                            flat_end=bool(c.get('along_per_variant')))""",
    """                            self.seed_plate(kk, _cc, _nrm, R, t,
                                            elong=(c.get('elong', 1.0)
                                                   if c.get('along_per_variant')
                                                   else 1.0),
                                            along=_along_of(kk),
                                            flat_end=bool(c.get('along_per_variant')),
                                            shape=c.get('nuc_shape', 'disc'))""",
    'fresh 通道')

# ③ stack 通道
rep("""                                self.seed_plate(k, cc, nrm, R, t,""",
    """                                self.seed_plate(k, cc, nrm, R, t,
                                                shape=c.get('nuc_shape', 'disc'),""",
    'stack 通道')

# ④ attach 通道
rep("""                                self.seed_plate(k_new, cc, nrm, R, _t_use,""",
    """                                self.seed_plate(k_new, cc, nrm, R, _t_use,
                                                shape=c.get('nuc_shape', 'disc'),""",
    'attach 通道')

io.open(P, 'w', encoding='utf-8').write(s)
print('  已改 %d 处：%s' % (len(cnt), cnt))
print('  文件长度 %d → %d' % (n0, len(s)))
