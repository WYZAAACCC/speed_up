#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cmp_cmd.py —— 比较「源进程命令行」与「生成的重启命令」的选项集合。"""
import os
import re
import sys

SRC_TAG = sys.argv[1] if len(sys.argv) > 1 else 't10PROD1'


def find(tag):
    me = str(os.getpid())
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or pid == me:
            continue
        try:
            raw = open('/proc/%s/cmdline' % pid, 'rb').read()
        except OSError:
            continue
        argv = [x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x]
        if any(x.endswith('_bk_exp.py') for x in argv[:4]) and tag in argv:
            return pid, argv
    return None, None


pid, argv = find(SRC_TAG)
print('源 PID =', pid)
src_keys = [a for a in argv if a.startswith('--')]
txt = open('_t11_relaunch_cmd.sh', encoding='utf-8').read()
gen_keys = re.findall(r'--([A-Za-z0-9-]+)', txt)
print('源 --选项数 =', len(src_keys))
print('生成 --选项数 =', len(gen_keys))
sk = set(k[2:] for k in src_keys)
gk = set(gen_keys)
print('\n**生成里缺的（源有、生成无）**：')
miss = sorted(sk - gk)
for k in miss:
    print('   ', k)
print('  （共 %d 个）' % len(miss))
print('\n**生成里多的**：', sorted(gk - sk))
print('\n源命令行长度 =', sum(len(a) + 1 for a in argv))
print('生成文件长度 =', len(txt))
