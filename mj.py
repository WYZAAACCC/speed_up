import urllib.request, urllib.parse, re, html, sys, io, time
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36','Accept-Language':'en-US,en;q=0.9'}
def mojeek(q):
    h=urllib.request.urlopen(urllib.request.Request('https://www.mojeek.com/search?q='+urllib.parse.quote(q),headers=UA),timeout=40).read().decode('utf-8','ignore')
    res=re.findall(r'<li>\s*<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>(.*?)</li>',h,re.S)
    out=[]
    for u,t,rest in res:
        p=re.search(r'<p class="s">(.*?)</p>',rest,re.S)
        cl=lambda x: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip()
        out.append((cl(t),u,cl(p.group(1)) if p else ''))
    return out
if __name__=='__main__':
    f=io.open(sys.argv[2],'w',encoding='utf-8')
    for q in sys.argv[1].split('||'):
        f.write('\n########## '+q+'\n')
        try:
            for t,u,d in mojeek(q): f.write('- %s\n  %s\n  %s\n'%(t,u,d[:400]))
        except Exception as e: f.write('ERR %s\n'%e)
        time.sleep(1)
    f.close()
