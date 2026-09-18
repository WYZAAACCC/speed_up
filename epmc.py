import urllib.request,urllib.parse,json,io,sys,time
UA={'User-Agent':'Mozilla/5.0'}
def s(q,n=15):
    u='https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='+urllib.parse.quote(q)+'&format=json&pageSize=%d&resultType=core'%n
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=45)).get('resultList',{}).get('result',[])
f=io.open(sys.argv[2],'w',encoding='utf-8')
for q in sys.argv[1].split('||'):
    f.write('\n########## '+q+'\n')
    try:
        for r in s(q):
            f.write('--- %s (%s) %s | OA=%s | PMCID=%s | DOI=%s\n'%(r.get('title'),r.get('pubYear'),r.get('journalTitle'),r.get('isOpenAccess'),r.get('pmcid'),r.get('doi')))
            ab=r.get('abstractText')
            if ab: f.write('    ABS: '+ab[:1500]+'\n')
    except Exception as e: f.write('ERR %s\n'%e)
    time.sleep(1)
f.close()
