import urllib.request, urllib.parse, re, html, sys, io, time
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
def bing(q,n=20):
    url='https://www.bing.com/search?q='+urllib.parse.quote(q)+'&format=rss&count=%d'%n
    h=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=40).read().decode('utf-8','ignore')
    items=re.findall(r'<item>(.*?)</item>',h,re.S)
    out=[]
    for it in items:
        def g(tag):
            m=re.search(r'<%s>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</%s>'%(tag,tag),it,re.S)
            return re.sub(r'\s+',' ',html.unescape(m.group(1))).strip() if m else ''
        out.append((g('title'),g('link'),g('description')))
    return out
if __name__=='__main__':
    f=io.open(sys.argv[2],'w',encoding='utf-8')
    for q in sys.argv[1].split('||'):
        f.write('\n########## '+q+'\n')
        try:
            for t,l,d in bing(q):
                f.write('- %s\n  %s\n  %s\n'%(t,l,d[:500]))
        except Exception as e: f.write('ERR %s\n'%e)
        time.sleep(1)
    f.close()
