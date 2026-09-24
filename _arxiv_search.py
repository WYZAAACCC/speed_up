#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_arxiv_search.py --- 找可复现的 Ti64 LPBF 晶粒仿真论文（明确初始条件 + 定量结果）'''
import json, urllib.request, urllib.parse, base64, os
OUT = '/mnt/f/speed_up/bench/exaca'
os.makedirs(OUT, exist_ok=True)


def gh(path):
    u = 'https://api.github.com/repos/LLNL/ExaCA/contents/%s?ref=master' % path
    req = urllib.request.Request(u, headers={'User-Agent': 'x'})
    return json.load(urllib.request.urlopen(req, timeout=30))


# 1) ExaCA 的 Inconel625 材料（拿到它的 V(dT) 闭式与 freezing range）
try:
    j = gh('examples/Materials/Inconel625.json')
    txt = base64.b64decode(j['content']).decode()
    open(os.path.join(OUT, 'Inconel625.json'), 'w').write(txt)
    print('=== ExaCA Inconel625.json:'); print(txt)
except Exception as e:
    print('!! 材料抓取失败:', e)

# 2) arXiv 检索
def arxiv(q, n=12):
    u = ('http://export.arxiv.org/api/query?search_query=%s&start=0&max_results=%d'
         '&sortBy=relevance' % (urllib.parse.quote(q), n))
    with urllib.request.urlopen(u, timeout=40) as r:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.read())
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    out = []
    for e in root.findall('a:entry', ns):
        out.append((e.find('a:id', ns).text.split('/abs/')[-1],
                    e.find('a:published', ns).text[:10],
                    ' '.join(e.find('a:title', ns).text.split())))
    return out

QS = [('CA+Ti64+LPBF', 'all:"cellular automaton" AND all:"Ti-6Al-4V" AND all:"additive manufacturing"'),
      ('grain+LPBF+Ti64', 'all:"laser powder bed" AND all:"Ti-6Al-4V" AND all:"grain" AND all:simulation'),
      ('ExaCA', 'all:"ExaCA"'),
      ('PF+Ti64+AM', 'all:"phase field" AND all:"Ti-6Al-4V" AND all:"additive manufacturing" AND all:"grain"')]
for tag, q in QS:
    print('\n=== arXiv 检索 [%s] %s' % (tag, q))
    try:
        for i, (aid, d, t) in enumerate(arxiv(q), 1):
            print('  %2d. %-22s %s  %s' % (i, aid, d, t[:96]))
    except Exception as e:
        print('  !! ', e)