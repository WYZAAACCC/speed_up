#!/usr/bin/env python3
"""Fetch Ti-6Al-4V / Ti-V solidification thermodynamics from open APIs (T5.1 step 2).

Only public bibliographic APIs: OpenAlex (works by DOI + search) and Crossref.
Prints ONLY the sentences that carry the quantities we need, so the output is
small enough to read.
"""
import json
import re
import urllib.parse
import urllib.request

UA = {'User-Agent': 'codex-lit/1.0 (mailto:wang@example.com)'}
KEYS = ('partition', 'partitioning', 'kov', 'k=', 'k =', 'liquidus', 'solidus',
        'distribution coefficient', 'tie line', 'segregation', 'enrich',
        'at.%', 'wt.%', 'temperature rang', 'melting')
NUMS = re.compile(r'\d')


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def uninv(inv):
    if not inv:
        return ''
    pos = {}
    for w, ps in inv.items():
        for p in ps:
            pos[p] = w
    return ' '.join(pos[k] for k in sorted(pos))


def sents(txt):
    txt = re.sub(r'\s+', ' ', txt)
    return [s.strip() for s in re.split(r'(?<=[.;])\s+', txt) if s.strip()]


def show(tag, txt, maxn=6):
    hit = [s for s in sents(txt) if any(k in s.lower() for k in KEYS) and NUMS.search(s)]
    if hit:
        print('  [%s]' % tag)
        for s in hit[:maxn]:
            print('    * ' + s[:400])


DOIS = ['10.1016/j.addma.2018.12.005', '10.1016/j.msea.2021.141237',
        '10.1016/j.actamat.2018.12.038', '10.1016/j.ijfatigue.2019.105358']
print('==== abstracts of the two target papers (+2) ====')
for doi in DOIS:
    try:
        d = get('https://api.openalex.org/works/https://doi.org/' + doi)
        print('\n%s (%s)  doi=%s' % (d.get('title'), d.get('publication_year'), doi))
        ab = uninv(d.get('abstract_inverted_index'))
        if not ab:
            print('    (no abstract in OpenAlex)')
        else:
            show('abs', ab)
    except Exception as e:
        print('  %s -> %s' % (doi, e))

QS = ['Ti-6Al-4V partition coefficient vanadium solidification beta',
      'Ti-V binary system partition coefficient liquidus solidus',
      'titanium alloy solidification microsegregation partition coefficient k',
      'Ti-6Al-4V liquidus solidus temperature',
      'vanadium redistribution beta titanium laser powder bed fusion segregation']
print('\n==== search hits (abstract-filtered) ====')
for q in QS:
    print('\n## %s' % q)
    try:
        r = get('https://api.openalex.org/works?search=%s&per-page=8'
                '&select=title,publication_year,doi,abstract_inverted_index'
                % urllib.parse.quote(q))
        for w in r.get('results', []):
            ab = uninv(w.get('abstract_inverted_index'))
            hit = [s for s in sents(ab)
                   if any(k in s.lower() for k in KEYS) and NUMS.search(s)]
            if hit:
                print(' * %s (%s) %s' % (w.get('title'), w.get('publication_year'),
                                         w.get('doi')))
                for s in hit[:3]:
                    print('     - ' + s[:360])
    except Exception as e:
        print('   search failed: %s' % e)