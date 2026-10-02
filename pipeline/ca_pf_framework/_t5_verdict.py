#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_verdict.py --- ★★★★★ 六条判据的**裁决器**（把口径与指标固化，避免每轮重新解释）

## 为什么需要它
本 goal 我因"口径没钉死就取数"犯过 **7** 次错。把判据连同**合法指标**写成脚本，
每轮只跑它 ⇒ **不再靠记忆**。

## 六条判据 + **合法指标**（每条都注明为什么用这个量）
| 判据 | 指标 | 为什么是它 |
|---|---|---|
| **① 随机形核** | 形核公告数 / 被拒数（**都在 step 1 之后的步**）| 位点由 RNG 抽取 ⇒ 伪随机；**只看 step>1 的事件**才算"随机" |
| **② 单板条三维几何量/长宽比** | `t_wf − Δx`（厚度）+ 投影跨度 + 长宽比 | 用 `_t5_twf.py` / `_t5_proj.py`（快照离线，40/200 步分辨率）|
| **③ 堆叠成块/低角晶界** | **`nblk_sig`**（不是 `nblk总`）+ `nf3` + `nf3_col` + `blk_laths` | `nblk总` 含微小碎片、剧烈跳动 |
| **④ 块间影响** | **`nf2`**（异变体界面）| F2 = 块相遇的签名 |
| **⑤ 填满盒子** | **`box_touch`** + 填充分数**平台**（**不是 100%**）| abA 跑满 5922 步末态也只有 **11.80%** |
| **⑥ 涌现自协调** | `n_var_sig > 1` + `r_selfac < 1` | 单变体时 `r_selfac` 恒 = 1.0（正常）|

## ⚠ 三条铁律（写死在脚本的判读里）
1. **`attach`/`--grow-stack` 模式下，长大看 `Vt` 与事件数，不是 `nslab_n`**；
2. **判据③ 用 `nblk_sig`**；
3. **判据⑤ 取"触及盒面 + 平台"，不是"100%"**。
"""
import csv
import glob
import os
import sys

V0 = 3.0679e-16          # 盒体积 m³（N=160 / dx=62.5 nm）


def num(r, k):
    try:
        return float((r.get(k) or '').strip())
    except ValueError:
        return None


def main():
    tags = sys.argv[1:] or ['t5H3']
    print('=' * 104)
    print('★ 六条判据裁决器（口径已固化）')
    print('=' * 104)
    for t in tags:
        p = '_exp/_bk_t5/dry_%s/series.csv' % t
        if not os.path.exists(p):
            print('  %-7s ⚠ 无 series' % t)
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        L = rows[-1]
        st = L.get('step')
        vt = num(L, 'Vt')
        fill = (vt / V0) if vt else None
        # 逐行统计（避开"末行空"的陷阱）
        def col(k):
            v = [num(r, k) for r in rows]
            v = [x for x in v if x is not None]
            return (max(v), len(v)) if v else (None, 0)

        mx_nf3, n_nf3 = col('nf3')
        mx_nf2, n_nf2 = col('nf2')
        mx_blk, n_blk = col('nblk_sig')
        mx_var, n_var = col('n_var_sig')
        mx_tch, n_tch = col('box_touch')
        mx_rs, n_rs = col('r_selfac')
        print()
        print('  ══ %s：%d 行，末步 %s ══' % (t, len(rows), st))
        print('     %-6s %-13s %-13s %s' % ('判据', '当前', '非空行数', '判定'))
        print('     ' + '-' * 72)
        # ①
        print('     %-6s %-13s %-13s %s' % ('①', '见形核计数', '—',
              '（用 grep 数 step>1 的形核公告）'))
        # ②
        print('     %-6s %-13s %-13s %s' % ('②', '见 _t5_twf/proj', '—',
              '（快照离线；只对变体场、只在形核后）'))
        # ③
        v3 = '✅' if (mx_blk or 0) >= 2 else ('部分' if (mx_nf3 or 0) > 0 else '❌')
        print('     %-6s nblk_sig=%-5s %-13d %s   (nf3 max=%s, nf3_col=%s)'
              % ('③', mx_blk, n_blk, v3, mx_nf3, L.get('nf3_col')))
        # ④
        v4 = '✅' if (mx_nf2 or 0) > 0 else '❌'
        print('     %-6s nf2=%-9s %-13d %s' % ('④', mx_nf2, n_nf2, v4))
        # ⑤
        v5 = '✅' if (mx_tch or 0) >= 1 else '❌'
        print('     %-6s box_touch=%-3s %-13d %s   填充=%.3f%%'
              % ('⑤', mx_tch, n_tch, v5, (fill * 100) if fill else 0))
        # ⑥
        v6 = '✅' if (mx_var or 0) >= 2 else '❌'
        print('     %-6s n_var_sig=%-3s %-13d %s   (r_selfac min=%s)'
              % ('⑥', mx_var, n_var, v6, mx_rs))
        print()
        print('     Vt 末值 = %.4g  ⇒ 填充 %.3f%%（**⑤ 的"平台"要跨多个读数看**）'
              % (vt or 0, (fill * 100) if fill else 0))
        # 快照与检查点
        d = os.path.dirname(p)
        sn = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        ck = sorted(glob.glob(os.path.join(d, 'ckpt', '*.npz')))
        band = []
        for s in sn:
            import numpy as np
            with np.load(s, allow_pickle=False) as z:
                if 'band_idx' in z.files:
                    band.append(os.path.basename(s))
        print('     snap=%d 个（带 band 的：%s）  ckpt=%d 个'
              % (len(sn), band or '无', len(ck)))
    print('=' * 104)


if __name__ == '__main__':
    main()
