#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ckpt_ls.py --- ★★★★★ 读一个检查点，**逐项报告它带了什么状态**

## 用途
1. **证明"该存的都存了"**（goal 任务(1) 的 1a–1k 逐项核对）；
2. **量真实体积**（每帧 MB）⇒ 验证 §4' 的成本定档；
3. **给恢复器（`--resume`）当规格书**：它该回填哪些键。
"""
import os
import pickle
import sys

import numpy as np

# goal 任务(1) 的 1a–1k ⇒ 键名映射（**逐项核对，缺一即报**）
SPEC = [
    ('1a  完整 φ（f64）',        ['phi']),
    ('1b  _nuc 整字典（pickle）', ['nuc_cfg_pkl']),
    ('1b  _nuc sites 位点池',     ['nuc_sites']),
    ('1b  ★ _nuc dbg[ok]',        ['nuc_ok']),
    ('1b  n_activated',           ['nuc_n_activated']),
    ('1d  ★ RNG 位发生器 state',  ['nuc_rng_state']),
    ('1c  t / T / df',            ['t', 'T', 'df']),
    ('1c  _cnt / _t_since_reinit', ['_cnt', '_t_since_reinit']),
    ('1c  _forced_reinit / _need_reinit', ['_forced_reinit', '_need_reinit']),
    ('1c  dG_max / _fp_cnt',      ['dG_max', '_fp_cnt']),
    ('1e  ★ _ae_eps',             ['ae_eps']),
    ('1e  ★ pf._eps0_lag',        ['pf_eps0_lag']),
    ('1e  pf.phi（物化档）',       ['pf_phi', 'pf_phi_mode']),
    ('1f  ★ npref_tab',           ['npref_pkl']),
    ('1g  c / Gam_mol / Gam / _Gam_derived / psi',
     ['aux_c', 'aux_Gam_mol', 'aux_Gam', 'aux_Gam_derived', 'aux_psi']),
    ('1h  ★ 模块全局 _UFV/_BBOX',  ['g_ufv_mode', 'g_bbox_mode']),
    ('1i  ★ 外部注入开关',         ['injected_pkl']),
    ('1j  ★ 驱动层 _qs_* + 计数',  ['drv_pkl', 'drv_dV']),
    ('1k  元信息（命令/哈希/精度）', ['cmdline', 'engine_sha', 'phi_prec', 'ckpt_ver']),
]


def main():
    p = sys.argv[1]
    if not os.path.exists(p):
        print('  ⚠ 没有 %s' % p)
        return
    z = np.load(p, allow_pickle=False)
    keys = set(z.files)
    print('=' * 100)
    print('检查点：%s' % p)
    print('  文件 %.2f MB；键 %d 个' % (os.path.getsize(p) / 1048576.0, len(keys)))
    print('=' * 100)
    print('  ── ★ goal 任务(1) 的 1a–1k **逐项核对** ──')
    miss = 0
    for name, ks in SPEC:
        got = [k for k in ks if k in keys]
        ok = len(got) == len(ks)
        if not ok:
            miss += len(ks) - len(got)
        print('   %s %-34s %s' % ('✅' if ok else '❌', name,
                                  '' if ok else ('缺: %s' % [k for k in ks if k not in keys])))
    print()
    print('  ⇒ **缺失项 %d**' % miss)
    print()
    print('  ── 关键量的实际形状 / dtype / 体积 ──')
    for k in sorted(keys):
        a = z[k]
        mb = a.nbytes / 1048576.0
        extra = ''
        if k == 'phi':
            extra = '  ★ **完整 φ** dtype=%s' % a.dtype
            if a.dtype != np.float64:
                extra += '  ❌ **不是 f64 ⇒ 违反 goal 硬要求！**'
            else:
                extra += '  ✅ f64'
        elif k == 'nuc_rng_state' and a.size:
            try:
                st = pickle.loads(a.tobytes())
                extra = '  ★ state keys=%s' % list(st)[:4]
            except Exception as e:
                extra = '  ⚠ 解不开：%s' % e
        elif k == 'nuc_cfg_pkl' and a.size:
            try:
                cfg = pickle.loads(a.tobytes())
                extra = '  ★ %d 个键' % len(cfg)
            except Exception as e:
                extra = '  ⚠ 解不开：%s' % e
        elif k == 'drv_pkl' and a.size:
            try:
                dv = pickle.loads(a.tobytes())
                extra = '  ★ %d 项：%s' % (len(dv), sorted(dv)[:6])
            except Exception as e:
                extra = '  ⚠ 解不开：%s' % e
        print('   %-18s %-22s %-10s %7.2f MB%s' % (k, str(a.shape), str(a.dtype), mb, extra))
    print()
    if 'cmdline' in keys:
        print('  复现命令：%s' % str(z['cmdline'])[:150])
    if 'engine_sha' in keys:
        print('  版本哈希：%s' % str(z['engine_sha'])[:150])
    print('=' * 100)


if __name__ == '__main__':
    main()
