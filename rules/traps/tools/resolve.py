import sqlite3,json,collections,sys,re,os,glob
c=sqlite3.connect(r'C:\GOG Games\Nox\dystopiannox\corpus\out\nox_corpus.db')
maps={m.lower():m for (m,) in c.execute('select name from maps')}
R=os.path.dirname(os.path.abspath(__file__))
WW=os.path.join(R,'..','ww'); OUT=os.path.join(R,'res'); os.makedirs(OUT,exist_ok=True)
for f in glob.glob(os.path.join(WW,'*.go')):
    base=os.path.basename(f)[:-3]
    M=maps.get(base.lower())
    src=open(f,encoding='utf-8').read()
    if not M or not src.strip(): continue
    types={}
    for t,scr in c.execute("select type,scr from objects where map=? and scr is not null and scr!=''",(M,)):
        types[scr]=t; types[scr.split(':')[-1]]=t
    assign=collections.defaultdict(set)
    for v,kind,name in re.findall(r'^\s*(\w+(?:\[\d+\])?) = ns\.(Object|Waypoint|WallGroup|ObjectGroup|WaypointGroup)\("([^"]+)"\)\s*$',src,re.M):
        pre={'Object':'O','Waypoint':'WP','WallGroup':'WALLS','ObjectGroup':'GRP','WaypointGroup':'WPG'}[kind]
        lab=f"{pre}<{name}" + (f":{types[name]}" if kind=='Object' and name in types else '') + ">"
        assign[v].add(lab)
    # wall vars
    for v,x,y in re.findall(r'^\s*(\w+) = ns\.Wall\((\d+), (\d+)\)\s*$',src,re.M):
        assign[v].add(f"WALL<{x},{y}>")
    lines=[]
    invar=False
    for line in src.split('\n'):
        if line.startswith('var ('): invar=True; continue
        if invar:
            if line.startswith(')'): invar=False
            continue
        if re.match(r'^\s*(\w+(?:\[\d+\])?) = ns\.(Object|Waypoint|WallGroup|ObjectGroup|WaypointGroup|Wall)\(',line): continue
        lines.append(line)
    out='\n'.join(lines)
    for v in sorted(assign,key=len,reverse=True):
        if len(assign[v])==1 and '[' not in v:
            out=re.sub(r'\b'+re.escape(v)+r'\b',next(iter(assign[v])),out)
    open(os.path.join(OUT,base+'.go'),'w',encoding='utf-8').write(out)
print('done')
