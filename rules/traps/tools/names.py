import sqlite3,json,collections,sys,re,os
c=sqlite3.connect(r'C:\GOG Games\Nox\dystopiannox\corpus\out\nox_corpus.db')
M=sys.argv[1]; F=sys.argv[2]
src=open(F,encoding='utf-8').read()
byscr={}
for i,t,scr,x,y,xf in c.execute("select id,type,scr,x,y,xfer from objects where map=?",(M,)):
    if scr:
        byscr[scr]=(i,t,x,y,xf); byscr[scr.split(':')[-1]]=(i,t,x,y,xf)
byid={i:(t,x,y) for i,t,x,y in c.execute("select extent,type,x,y from objects where map=?",(M,))}
for n in sorted(set(re.findall(r'ns\.Object\("([^"]+)"\)',src))):
    r=byscr.get(n)
    if r:
        extra=''
        if r[4] and r[1] in ('Mover',):
            d=json.loads(r[4]); extra=f" speed={d.get('MovingSpeed')} type={d.get('MoveType')} wp={d.get('WaypointID')}"
        if r[4] and r[1].startswith('SentryGlobe'):
            extra=' '+r[4][:200]
        print(f"OBJ {n}: {r[1]} @{int(r[2])},{int(r[3])}{extra}")
    else: print(f"OBJ {n}: ??")
groups={}
for name,typ,n,mem in c.execute("select name,type,n,members from groups_ where map=?",(M,)):
    groups[name.split(':')[-1]]=(typ,json.loads(mem))
for n in sorted(set(re.findall(r'ns\.(?:Object|Wall|Waypoint)Group\("([^"]+)"\)',src))):
    g=groups.get(n)
    if not g: print('GRP',n,'??'); continue
    typ,mem=g
    if typ=='objects':
        cnt=collections.Counter(byid[m][0] for m in mem if m in byid)
        xs=[byid[m][1] for m in mem if m in byid]; ys=[byid[m][2] for m in mem if m in byid]
        bb=f" bbox=({int(min(xs))},{int(min(ys))})-({int(max(xs))},{int(max(ys))})" if xs else ''
        print(f"GRP {n} objects {dict(cnt)}{bb}")
    else:
        print(f"GRP {n} {typ} n={len(mem)} {str(mem)[:120]}")
