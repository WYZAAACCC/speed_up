import re
p="/mnt/f/speed_up/pipeline/gibbs/prod3d/results_g3d2d_dbg/case.i"
t=open(p,encoding="utf-8",errors="replace").read().split("\n")
depth=0
for i,l in enumerate(t,1):
    s=l.strip()
    if not s or s.startswith("#"): continue
    if s=="[]":
        depth-=1
        continue
    m=re.match(r"^\[([^\]]+)\]$",s)
    if m and len(l)-len(l.lstrip())==depth*2:
        print("%5d %s%s"%(i,"  "*depth,s))
        depth+=1
