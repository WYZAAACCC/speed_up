#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：只读清点 `snap_*.npz` 的 keys / shape / dtype（不整载入）。
**新增文件，不改任何已有文件。**
用法: python3 _r30_snapinv.py <算例目录 ...>
"""
import os
import sys
import glob
import json

import numpy as np


def inv(p):
    st = os.stat(p)
    out = dict(path=p, size=st.st_size, mtime=st.st_mtime)
    try:
        z = np.load(p, allow_pickle=False)
    except Exception as e:                                  # noqa: BLE001
        out['error'] = repr(e)
        return out
    keys = []
    for k in z.files:
        a = z[k]
        item = dict(key=k, shape=list(a.shape), dtype=str(a.dtype),
                    nbytes=int(a.nbytes))
        if a.dtype.kind in 'iu' and a.size <= 64:
            item['values'] = a.tolist()
        elif a.dtype.kind in 'f' and a.size <= 8:
            item['values'] = [float(v) for v in a.ravel()]
        elif a.dtype.kind == 'U' and a.size <= 64:
            item['values'] = a.tolist()
        keys.append(item)
    out['keys'] = keys
    z.close()
    return out


def main(dis):
    res = []
    for d in dis:
        for p in sorted(glob.glob(os.path.join(d, 'snap_*.npz'))):
            res.append(inv(p))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
