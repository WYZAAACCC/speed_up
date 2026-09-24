#!/usr/bin/env python3
"""只跑 M4（守恒）以快速迭代"""
import sys
import windowB_surface as W
if len(sys.argv) > 1 and sys.argv[1] == 'm3':
    print(W.M3_McLean())
elif len(sys.argv) > 1 and sys.argv[1] == 'both':
    print(W.M3_McLean())
    print(W.M4_conservation())
else:
    print(W.M4_conservation())
