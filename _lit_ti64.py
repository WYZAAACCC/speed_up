#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_lit_ti64.py --- arXiv 检索：Ti64 马氏体/Burgers 变体的【转变应变】与晶格参数'''
import json, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

def arxiv(q, n=10):
    u = ('http://export.arxiv.org/api/query?search_query=%s&start=0&max_results=%d&sortBy=relevance'
         % (urllib.parse.quote(q), n))
    for _ in range(3):
        try:
            with urllib.request.urlopen(u, timeout=45) as r:
                root = ET.fromstring(r.read())
            break
        except Exception as e:
            print('   重试:', e); time.sleep(5)
    else:
        return []
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    out = []
    for e in root.findall('a:entry', ns):
        out.append((e.find('a:id', ns).text.split('/abs/')[-1],
                    e.find('a:published', ns).text[:10],
                    ' '.join(e.find('a:title', ns).text.split())))
    return out

QS = [('Ti64 martensite PF', 'all:"Ti-6Al-4V" AND all:"phase field" AND all:martensite'),
      ('Burgers variant strain', 'all:"Burgers orientation relationship" AND all:"transformation strain"'),
      ('Ti64 variant selection', 'all:"variant selection" AND all:"Ti-6Al-4V"'),
      ('Ti64 alpha prime PF', 'all:"alpha prime" AND all:"Ti-6Al-4V" AND all:simulation'),
      ('Ti hcp bcc eigenstrain', 'all:"bcc" AND all:"hcp" AND all:"transformation strain" AND all:titanium')]
for tag, q in QS:
    print('\n=== [%s] %s' % (tag, q))
    for i, (aid, d, t) in enumerate(arxiv(q), 1):
        print('  %2d. %-22s %s  %s' % (i, aid, d, t[:100]))
    time.sleep(3)