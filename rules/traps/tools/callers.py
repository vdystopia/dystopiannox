import sqlite3,json,collections,sys
c=sqlite3.connect(r'C:\GOG Games\Nox\dystopiannox\corpus\out\nox_corpus.db')
M=sys.argv[1]
bits=['MISSILE','MONSTER','PLAYER','OBSTACLE','FOOD','EXIT','KEY','DOOR','INFO_BOOK','TRIGGER','TRANSPORTER','HOLE','WAND','FIRE','ELEVATOR','ELEVATOR_SHAFT','DANGEROUS','MONSTERGENERATOR','READABLE','LIGHT','SIMPLE','COMPLEX','IMMOBILE','VISIBLE_ENABLE','WEAPON','ARMOR','NOT_STACKABLE','TREASURE','FLAG','CLIENT_PERSIST','CLIENT_PREDICT','PICKUP']
def dec(v): return '|'.join(b[:4] for i,b in enumerate(bits) if v>>i&1) or 'ANY'
ev=['Sighted','Looking','DEATH','Focus','Hit','Retreat','Collide','Heard','EndWP','Lost']
funcs=set(n for (n,) in c.execute('select name from script_funcs where map=?',(M,)))
out=collections.defaultdict(list)
for i,t,xt,x,scr,ox,oy in c.execute("select id,type,xtype,xfer,scr,x,y from objects where map=? and xfer is not null and xfer!=''",(M,)):
    try: d=json.loads(x)
    except: continue
    if xt=='TriggerXfer':
        for k,short in (('ScriptOnPressed','P'),('ScriptOnReleased','R'),('ScriptOnCollided','C')):
            if d.get(k) in funcs:
                out[d[k]].append(f"{t}#{i}{'('+scr+')' if scr else ''}@{int(ox)},{int(oy)} {short} {d['SizeX']}x{d['SizeY']} allow={dec(d['AllowedObjClass'])}{' ign='+dec(d['IgnoredObjClass']) if d['IgnoredObjClass'] else ''}")
    elif 'ScriptEvents' in d:
        for j,v in enumerate(d['ScriptEvents']):
            if v in funcs: out[v].append(f"{t}#{i}{'('+scr+')' if scr else ''}@{int(ox)},{int(oy)} ev={ev[j]}")
    else:
        for k,v in d.items():
            if isinstance(v,str) and v in funcs: out[v].append(f"{t}#{i}{'('+scr+')' if scr else ''}@{int(ox)},{int(oy)} {k}")
for n,ep in c.execute("select name,enter_player from polygons where map=? and enter_player!=''",(M,)):
    out[ep].append(f"POLYGON {n} enter")
for f in sorted(out):
    L=out[f]
    if len(L)>4:
        cnt=collections.Counter(s.split('#')[0]+' '+' '.join(s.split(' ')[1:]) for s in L)
        print(f, f"[{len(L)}]", '; '.join(L[:3]), '| ...', dict(cnt))
    else:
        print(f, '<-', '; '.join(L))
