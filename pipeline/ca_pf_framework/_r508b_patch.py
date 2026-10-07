#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r508b_patch.py —— `shape` 接线的剩下三处：`nuc_cfg` 参数、`c['nuc_shape']`、探针调用点。"""
import io

P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
ok = []


def rep(old, new, tag):
    global s
    if old not in s:
        print('  ❌ 找不到：%s' % tag)
        return
    s = s.replace(old, new, 1)
    ok.append(tag)


# ① nuc_cfg 签名加 shape
rep("""    def nuc_cfg(self, R_nuc, t_nuc, gamma=0.15, n_init=0, p_auto=0.0,""",
    """    def nuc_cfg(self, R_nuc, t_nuc, gamma=0.15, n_init=0, p_auto=0.0,
                shape='disc',""",
    'nuc_cfg 签名')

# ② c 字典里加 nuc_shape
rep("""                         supercrit=bool(supercrit),""",
    """                         supercrit=bool(supercrit),
                         # ★ R508：**核的形状**。'disc'（默认，= 归档行为）
                         #   或 'ellipsoid'。详见 `seed_plate` 里的长注释与
                         #   `R507_fullclosure`：尖边圆柱的弹性罚比光滑椭球高 52%，
                         #   把形核窗口从 344 K 压到 80 K，导致 C3 与块厚带无法同时满足。
                         nuc_shape=str(shape),""",
    "c['nuc_shape']")

# ③ 探针调用点传 shape
rep("""                            _ok_sc, _med_sc, _fc_sc, _n_sc = self._supercrit_probe(
                                kk, _cc, _nrm, R, t, _cover, df, c['gamma'])""",
    """                            _ok_sc, _med_sc, _fc_sc, _n_sc = self._supercrit_probe(
                                kk, _cc, _nrm, R, t, _cover, df, c['gamma'],
                                shape=c.get('nuc_shape', 'disc'))""",
    '探针调用点')

io.open(P, 'w', encoding='utf-8').write(s)
print('  已改 %d 处：%s' % (len(ok), ok))
