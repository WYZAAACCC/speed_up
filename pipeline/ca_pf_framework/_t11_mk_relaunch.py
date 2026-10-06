#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_mk_relaunch.py —— 从**正在跑的进程命令行**生成重启命令（只改指定项）。

## 为什么这样做（而不是手抄）
  `t10PROD1` 的命令行有 **126 个长选项**；手抄极易漏/错（本会话已因手写键清单
  漏掉 `--burst-km` 而出过一次事故 ⇒ 生产 `_tgt` 被钉在 9 而不是 135）。
  ⇒ **从 `/proc/<pid>/cmdline` 逐字取回**，只覆盖要改的项。

## 用法
  _t11_mk_relaunch.py <源tag> <新tag> [k=v ...]
  例：_t11_mk_relaunch.py t10PROD1 t10PROD2 wrap_every=20 evloc=1
"""
import os
import subprocess
import sys

FLAG_LIKE = {"closed", "closed-force", "diag-edv", "diag-terms", "dry-run",
             "eng-force-reinit", "eng-no-force-reinit", "grow-stack",
             "mob-wulff", "multi-block", "nuc-compensate"}


def find_cmd(tag):
    """在 /proc 里找命令行含 `--tag <tag>` 的 python 进程，返回 argv 列表。"""
    me = str(os.getpid())
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or pid == me:
            continue
        try:
            with open('/proc/%s/cmdline' % pid, 'rb') as fh:
                raw = fh.read()
        except OSError:
            continue
        argv = [x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x]
        # ⚠ 第一版写成 `argv[1].endswith('_bk_exp.py')` —— **错的**：
        #   命令行是 `python -u _bk_exp.py …` ⇒ `argv[1]` 是 `-u`，脚本在 `argv[2]`。
        #   ⇒ 改成**整条 argv 里找**。
        if not any(x.endswith('_bk_exp.py') for x in argv[:4]):
            continue
        if '--tag' in argv and tag in argv:
            return pid, argv
    return None, None


def to_kv(argv):
    """argv → 有序 (key, value|None) 列表（value=None 表示 store_true 旗标）。"""
    out, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a.startswith('--'):
            k = a[2:]
            if k in FLAG_LIKE:
                out.append((k, None))
                i += 1
            else:
                out.append((k, argv[i + 1] if i + 1 < len(argv) else ''))
                i += 2
        else:
            i += 1
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, new = sys.argv[1], sys.argv[2]
    over = {}
    for s in sys.argv[3:]:
        k, _, v = s.partition('=')
        over[k.replace('_', '-')] = v

    pid, argv = find_cmd(src)
    if argv is None:
        sys.exit('**找不到 tag=%s 的进程**' % src)
    print('源进程 PID=%s（tag=%s）' % (pid, src))
    kv = to_kv(argv)
    print('解析出 %d 个选项' % len(kv))

    d = dict(kv)
    d['tag'] = new
    for k, v in over.items():
        if k not in d:
            print('  ⚠ 新增选项 `--%s`（源命令行里本来没有）' % k)
        d[k] = v
    # `--out` 必须保留（R619 §7 的事故：漏 `--out` 会写到 `_exp/_bk_block`）
    if 'out' not in d or not d['out']:
        sys.exit('**`--out` 缺失或为空 ⇒ 拒绝生成**（R619 §7 的教训）')

    parts = ['/root/miniconda3/envs/ml/bin/python', '-u', '_bk_exp.py']
    for k, v in kv:                       # 保持源顺序
        vv = d.get(k, v)
        if vv is None:
            parts.append('--' + k)
        else:
            parts += ['--' + k, str(vv)]
    for k in d:                           # 源里没有的新选项
        if k not in dict(kv):
            vv = d[k]
            parts.append('--' + k)
            if vv is not None:
                parts.append(str(vv))

    # ★ 自检（R619 §7 之后立的规矩）
    must = ['--out', '--tag', '--pf-phi', '--burst-km', '--steps', '--wrap-every',
            '--evloc', '--nuc-shape', '--nuc-block-target']
    txt = ' '.join(parts)
    for m in must:
        if m not in parts and not any(p == m for p in parts):
            sys.exit('**自检失败：缺少 %s**' % m)
    print('\n★ 自检通过（%d 个 token，关键项齐）' % len(parts))
    with open('_t11_relaunch_cmd.sh', 'w') as fh:
        fh.write('#!bin/bash\n# 自动生成：_t11_mk_relaunch.py\n')
        fh.write('cd /mnt/f/speed_up/pipeline/ca_pf_framework\n')
        fh.write('exec ' + ' '.join("'%s'" % p if ' ' in p else p
                                    for p in parts) + '\n')
    print('已写出 `_t11_relaunch_cmd.sh`')
    print('  新 tag = %s ; 覆盖项 = %s' % (new, over))


if __name__ == '__main__':
    main()
