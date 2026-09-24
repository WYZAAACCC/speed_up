#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_exaca_fetch.py --- 用 GitHub API 取 ExaCA 的算例输入（raw 域名可能不可达，改走 API+base64）'''
import json, os, base64, urllib.request, sys
OUT = '/mnt/f/speed_up/bench/exaca'
os.makedirs(OUT, exist_ok=True)
REPO = 'LLNL/ExaCA'
REF = 'master'
API = 'https://api.github.com/repos/%s/contents/%s?ref=%s'


def get(path):
    req = urllib.request.Request(API % (REPO, path, REF), headers={'User-Agent': 'curl'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def save(path, dest=None):
    j = get(path)
    if isinstance(j, list):
        out = []
        for it in j:
            out.append((it['name'], it['type'], it.get('size')))
            if it['type'] == 'file':
                sub = dest or OUT
                os.makedirs(sub, exist_ok=True)
                try:
                    jj = get(it['path'])
                    data = base64.b64decode(jj['content'])
                    with open(os.path.join(sub, it['name']), 'wb') as f:
                        f.write(data)
                except Exception as e:
                    print('   !! %s: %s' % (it['name'], e))
        return out
    return j


print('=== examples/Materials')
for nm, tp, sz in save('examples/Materials'):
    print('   %-28s %-5s %s' % (nm, tp, sz))
print('=== examples/Substrate')
for nm, tp, sz in save('examples/Substrate'):
    print('   %-28s %-5s %s' % (nm, tp, sz))
print('=== 关键算例 json')
for f in ('Inp_TwoGrainDirSolidification.json', 'Inp_DirSolidification.json',
          'Inp_SmallDirSolidification.json', 'Inp_EquiaxedGrain.json',
          'Inp_SingleLine.json', 'README.md'):
    try:
        j = get('examples/' + f)
        open(os.path.join(OUT, f), 'wb').write(base64.b64decode(j['content']))
        print('   saved %-38s %d B' % (f, j['size']))
    except Exception as e:
        print('   !! %s: %s' % (f, e))