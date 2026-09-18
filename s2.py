import urllib.request,urllib.parse,json,io,sys,time
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
def s2(q,limit=10):
    u=('https://api.semanticscholar.org/graph/v1/paper/search?query='+urllib.parse.quote(q)
       +'&limit=%d&fields=title,year,venue,abstract,externalIds,citationCount'%limit)
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40)).get('data',[])
        except Exception as e:
            time.sleep(4)
    return []
f=io.open(sys.argv[2],'w',encoding='utf-8')
for q in sys.argv[1].split('||'):
    f.write('\n########## '+q+'\n')
    for p in s2(q):
        f.write('--- %s (%s) %s | cites=%s | %s\n'%(p.get('title'),p.get('year'),p.get('venue'),p.get('citationCount'),(p.get('externalIds') or {}).get('DOI')))
        ab=p.get('abstract')
        if ab: f.write('    ABS: '+ab[:1200].replace('\n',' ')+'\n')
    time.sleep(2)
f.close()
