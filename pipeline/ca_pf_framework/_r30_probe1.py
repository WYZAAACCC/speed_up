#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30 只读审计：探针 1 —— snap_*.npz 里有什么、series.csv 里有什么。"""
import os
import sys
import glob
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)


def show(path):
    print('=' * 90)
    print(path, '%.1f MB' % (os.path.getsize(path) / 1e6))
    with np.load(path) as d:
        for k in d.files:
            a = d[k]
            print('   %-16s shape=%-22s dtype=%-10s' % (k, str(a.shape), a.dtype))


def main():
    for p in sys.argv[1:]:
        show(p)


if __name__ == '__main__':
    main()
