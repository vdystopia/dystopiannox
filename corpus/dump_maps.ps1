# Exports Nox maps (and the game's thing database) to JSON through the editor's library, so values
# are exactly what the editor sees. Run in 32-bit PowerShell; corpus\build_corpus.py drives it.
#   -MapList: text file, one .map path per line.  -OutDir: receives <name>.json per map + things.json
# The export itself is C# (compiled below) because PowerShell's JSON tools are too slow and run
# out of memory on large maps.
param(
    [Parameter(Mandatory)] [string]$MapList,
    [Parameter(Mandatory)] [string]$OutDir
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$dll = Join-Path $repo 'Shared\bin\Release\NoxShared.dll'
Add-Type -AssemblyName System.Drawing, System.Web.Extensions
Add-Type -Path $dll
Add-Type -ReferencedAssemblies $dll, System.Drawing, System.Web.Extensions -TypeDefinition @'
using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;
using NoxShared;

public static class CorpusDump
{
    const BindingFlags Pub = BindingFlags.Public | BindingFlags.Instance;
    static readonly FieldInfo XferField = typeof(Map.Object).GetField("ExtraData", BindingFlags.NonPublic | BindingFlags.Instance);
    static readonly FieldInfo HeaderField = typeof(Map).GetField("Header", BindingFlags.NonPublic | BindingFlags.Instance);

    static object Simple(object v, int depth)
    {
        if (v == null) return null;
        if (v is string || v is bool || v.GetType().IsPrimitive) return v;
        if (v is Enum) return v.ToString();
        if (v is Color) { var c = (Color)v; return new object[] { c.R, c.G, c.B }; }
        if (v is PointF) { var p = (PointF)v; return new object[] { p.X, p.Y }; }
        if (v is Point) { var p = (Point)v; return new object[] { p.X, p.Y }; }
        if (v is byte[]) return ((byte[])v).Length;          // raw blobs: keep only the size
        var en = v as IEnumerable;
        if (en != null)
        {
            var list = new List<object>();
            foreach (var i in en) { if (list.Count >= 64) break; list.Add(Simple(i, depth + 1)); }
            return list;
        }
        if (depth >= 2) return v.ToString();
        var d = new Dictionary<string, object>();
        foreach (var f in v.GetType().GetFields(Pub)) if (!f.IsLiteral) d[f.Name] = Simple(f.GetValue(v), depth + 1);
        return d;
    }

    static Dictionary<string, object> Obj(Map.Object o)
    {
        var x = XferField.GetValue(o);
        var xf = new Dictionary<string, object>();
        if (x != null) foreach (var f in x.GetType().GetFields(Pub)) if (!f.IsLiteral) xf[f.Name] = Simple(f.GetValue(x), 0);
        var inv = new List<object>();
        foreach (Map.Object i in o.InventoryList) inv.Add(Obj(i));
        return new Dictionary<string, object> {
            {"t", o.Name}, {"x", o.Location.X}, {"y", o.Location.Y}, {"ext", o.Extent}, {"team", o.Team},
            {"scr", o.Scr_Name}, {"term", o.Terminator}, {"cflags", o.CreateFlags}, {"anim", o.AnimFlags},
            {"pickup", o.pickup_func}, {"xtype", x == null ? null : x.GetType().Name}, {"xfer", xf}, {"inv", inv} };
    }

    public static string DumpMap(string path, string outFile)
    {
        Map map;
        using (var fs = File.OpenRead(path)) map = new Map(new NoxBinaryReader(fs, CryptApi.NoxCryptFormat.MAP));
        var hdr = HeaderField.GetValue(map);
        var walls = new List<object>();
        foreach (Point k in map.Walls.Keys)
        {
            var w = map.Walls[k];
            var extra = new Dictionary<string, object>();
            foreach (var f in w.GetType().GetFields(Pub))
            {
                if (f.Name == "Location" || f.Name == "Facing" || f.Name == "matId" || f.Name == "Variation" || f.Name == "Minimap") continue;
                var v = f.GetValue(w);
                if (v == null || (v is bool && !(bool)v) || (v.GetType().IsPrimitive && Convert.ToDouble(v) == 0) || (v is string && (string)v == "")) continue;
                extra[f.Name] = Simple(v, 0);
            }
            walls.Add(new object[] { k.X, k.Y, (int)w.Facing, (int)w.matId, (int)w.Variation, (int)w.Minimap, extra });
        }
        var tiles = new List<object>();
        foreach (Point k in map.Tiles.Keys)
        {
            var t = map.Tiles[k];
            var edges = new List<object>();
            foreach (Map.Tile.EdgeTile e in t.EdgeTiles) edges.Add(new object[] { (int)e.Graphic, (int)e.Variation, (int)e.Dir, (int)e.Edge });
            tiles.Add(new object[] { k.X, k.Y, (int)t.graphicId, (int)t.Variation, edges });
        }
        var objects = new List<object>();
        foreach (Map.Object o in map.Objects) objects.Add(Obj(o));
        var wps = new List<object>();
        foreach (Map.Waypoint w in map.Waypoints)
        {
            var links = new List<object>();
            foreach (Map.Waypoint.WaypointConnection c in w.connections) links.Add(new object[] { c.wp == null ? c.wp_num : c.wp.Number, (int)c.flag });
            wps.Add(new Dictionary<string, object> { {"n", w.Number}, {"name", w.Name}, {"x", w.Point.X}, {"y", w.Point.Y}, {"flags", w.Flags}, {"links", links} });
        }
        var polys = new List<object>();
        foreach (Map.Polygon p in map.Polygons)
        {
            var pts = new List<object>();
            foreach (PointF q in p.Points) pts.Add(new object[] { q.X, q.Y });
            polys.Add(new Dictionary<string, object> { {"name", p.Name}, {"amb", Simple(p.AmbientLightColor, 0)}, {"mm", p.MinimapGroup},
                {"secret", p.IsQuestSecret}, {"enterP", p.EnterFuncPlayer}, {"enterM", p.EnterFuncMonster}, {"pts", pts} });
        }
        var groups = new List<object>();
        foreach (string k in map.Groups.Keys)
        {
            var g = map.Groups[k];
            var members = new List<object>();
            foreach (var m in g) members.Add(Simple(m, 0));
            groups.Add(new Dictionary<string, object> { {"name", (g.name ?? "").TrimEnd('\0')}, {"type", g.type.ToString()}, {"members", members} });
        }
        var funcs = new List<object>();
        foreach (var f in map.Scripts.Funcs) funcs.Add(f.name);
        var i = map.Info;
        var doc = new Dictionary<string, object> {
            {"name", Path.GetFileNameWithoutExtension(path)}, {"file", path},
            {"info", new Dictionary<string, object> { {"summary", i.Summary}, {"description", i.Description}, {"author", i.Author},
                {"version", i.Version}, {"date", i.Date}, {"type", (uint)i.Type}, {"min", i.RecommendedMin}, {"max", i.RecommendedMax},
                {"qintro", i.QIntroTitle}, {"qgraphic", i.QIntroGraphic} }},
            {"header", Simple(hdr, 0)}, {"ambient", Simple(map.Ambient.AmbientColor, 0)}, {"intro", map.Intro.Text},
            {"walls", walls}, {"tiles", tiles}, {"objects", objects}, {"waypoints", wps}, {"polygons", polys}, {"groups", groups},
            {"script", new Dictionary<string, object> { {"funcs", funcs}, {"strings", new List<string>(map.Scripts.SctStr)} }} };
        Save(doc, outFile);
        return string.Format("walls={0} tiles={1} objects={2} waypoints={3}", walls.Count, tiles.Count, objects.Count, wps.Count);
    }

    public static void DumpThings(string outFile)
    {
        var things = new List<object>();
        foreach (var kv in ThingDb.Things)
        {
            var t = kv.Value;
            things.Add(new Dictionary<string, object> { {"name", kv.Key}, {"class", t.Class.ToString()}, {"subclass", Simple(t.Subclass, 0)},
                {"xfer", t.Xfer}, {"flags", t.Flags.ToString()}, {"ext", t.ExtentType}, {"ex", t.ExtentX}, {"ey", t.ExtentY}, {"health", t.Health} });
        }
        var floors = new List<object>();
        foreach (var f in ThingDb.FloorTiles) floors.Add(new Dictionary<string, object> { {"name", f.Name}, {"rows", f.numRows}, {"cols", f.numCols}, {"nvar", f.Variations.Count} });
        var walls = new List<object>();
        foreach (var w in ThingDb.Walls) walls.Add(new Dictionary<string, object> { {"name", w.Name}, {"nvar", w.Variations} });
        var edges = new List<object>();
        foreach (var e in ThingDb.EdgeTiles) edges.Add(new Dictionary<string, object> { {"name", e.Name}, {"nvar", e.Variations.Count} });
        Save(new Dictionary<string, object> { {"things", things}, {"floors", floors}, {"walls", walls}, {"edges", edges} }, outFile);
    }

    static void Save(object doc, string outFile)
    {
        var js = new JavaScriptSerializer();
        js.MaxJsonLength = int.MaxValue;
        js.RecursionLimit = 64;
        File.WriteAllText(outFile, js.Serialize(doc), new UTF8Encoding(false));
    }
}
'@

New-Item -ItemType Directory -Force $OutDir | Out-Null
foreach ($path in (Get-Content -Encoding UTF8 $MapList | Where-Object { $_ })) {
    $name = [IO.Path]::GetFileNameWithoutExtension($path)
    try { "OK`t$name`t" + [CorpusDump]::DumpMap($path, (Join-Path $OutDir "$name.json")) }
    catch { "FAIL`t$name`t$($_.Exception.GetBaseException().Message)" }
}
[CorpusDump]::DumpThings((Join-Path $OutDir 'things.json'))
"OK`tthings.json"
