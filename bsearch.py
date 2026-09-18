import urllib.request, urllib.parse, re, html, sys, io, time
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36','Accept-Language':'en-US,en;q=0.9'}
def search(q, n=20):
    url='https://cn.bing.com/search?q='+urllib.parse.quote(q)+'&count=%d&setlang=en'%n
    req=urllib.request.Request(url, headers=UA)
    h=urllib.request.urlopen(req, timeout=40).read().decode('utf-8','ignore')
    items=re.findall(r'<li class="b_algo".*?</li>', h, re.S)
    res=[]
    for it in items:
        t=re.search(r'<h2>(.*?)</h2>', it, re.S)
        u=re.search(r'href="(http[^"]+)"', it)
        p=re.search(r'<p[^>]*>(.*?)</p>', it, re.S)
        def clean(x):
            return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip() if x else ''
        res.append((clean(t.group(1) if t else ''), u.group(1) if u else '', clean(p.group(1) if p else '')))
    return res
if __name__=='__main__':
    out=io.open(sys.argv[2],'w',encoding='utf-8')
    for q in sys.argv[1].split('||'):
        out.write('\n########## '+q+'\n')
        try:
            for t,u,p in search(q):
                out.write('- %s\n  %s\n  %s\n'%(t,u,p[:400]))
        except Exception as e:
            out.write('ERR %s\n'%e)
        time.sleep(1)
    out.close()
