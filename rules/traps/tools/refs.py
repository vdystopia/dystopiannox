import sqlite3,json,collections,sys
c=sqlite3.connect(r'C:\GOG Games\Nox\dystopiannox\corpus\out\nox_corpus.db')
funcs=collections.defaultdict(set)
for m,n in c.execute('select map,name from script_funcs'): funcs[m].add(n)
keys=collections.Counter()
refs=[]
def walk(v,path):
    if isinstance(v,dict):
        for k,vv in v.items(): yield from walk(vv,path+[k])
    elif isinstance(v,list):
        for i,vv in enumerate(v): yield from walk(vv,path+[str(i)])
    elif isinstance(v,str) and v:
        yield path,v
for m,i,t,xt,x,scr,ox,oy in c.execute("select map,id,type,xtype,xfer,scr,x,y from objects where xfer is not null and xfer!=''"):
    try: d=json.loads(x)
    except: continue
    for p,v in walk(d,[]):
        if v in funcs[m]:
            keys[(xt,'.'.join(p))]+=1
            refs.append((m,i,t,xt,'.'.join(p),v,scr,ox,oy))
for k,v in keys.most_common(): print(k,v)
json.dump(refs,open(sys.argv[1],'w'))
