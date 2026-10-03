using System;
using System.Collections;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using NoxShared;
using System.CodeDom;
using System.CodeDom.Compiler;
using System.Drawing.Drawing2D;
using System.Collections.Generic;
using MapEditor.render;
//using MapEditor.noxscript2;
using MapEditor.newgui;
using MapEditor.MapInt;
using System.Linq;

namespace MapEditor
{
    public class MainWindow : Form
    {
        #region Globals
        // Change version number in Project Properties
        private const string TITLE_FORMAT = "Nox Map Editor {2}: {0} ({1}{3})";
        public int mapZoom = 2;
        public int mapDimension = 256;
        public bool RightDown = false;
        public bool suggestBlocked = false;
        public Point mouseLocation;
        public MapView mapView;
        public FlickerFreePanel miniViewPanel;
        public static MainWindow Instance;
        public Minimap minimap;
        protected IList cultures;
        protected Map map
        {
            get
            {
                return MapInterface.TheMap;
            }
        }
        private bool added;
        private bool moved = false;
        private string scriptPath;
        private Bitmap lastMapImage;
        private Rectangle redraw;
        private ToolStripMenuItem menuSaveNXZOnly;
        private ToolStripMenuItem menuWaypoints;
        public ListBox suggestBox;
        private ToolStripMenuItem menuHelpLink5;
        private Process nsdc = null;

        public class FlickerFreePanel : Panel
        {
            // set styles to reduce flicker and painting over twice
            public FlickerFreePanel() : base()
            { SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.Opaque, true); }
        }
        #endregion
        #region Main Window
        [STAThread]
        static void Main(string[] args)
        {
            Logger.Init();

#if !DEBUG
            try
            {
#endif
            Application.Run(new MainWindow(args));
#if !DEBUG
			}
			catch (Exception ex)
			{
				new ExceptionDialog(ex, "Exception in main loop").ShowDialog();
				Environment.Exit(-1);
			}
#endif
        }
        public MainWindow(string[] args)
        {
            Instance = this;
            // Show the loading splash screen
            Splash spl = new Splash();
            spl.Show();
            spl.Refresh();
            // Setup locales
            cultures = GetSupportedCultures();
            minimap = new Minimap();
            InitializeComponent();

            if (EditorSettings.Default.IsMaximized)
                WindowState = FormWindowState.Maximized;
            else
            {
                if (EditorSettings.Default.SaveSize != new Size(0, 0))
                    Size = EditorSettings.Default.SaveSize;
            }

            // Set up map type selector (arena by default)
            mapType.Items.AddRange(new ArrayList(Map.MapInfo.MapTypeNames.Values).ToArray());
            mapType.SelectedIndex = 3;
            // Load categories.xml
            mapView.LoadObjectCategories();
            // Create noxscript\nsc.exe and nsdc.exe
            CreateScriptDependancies();
            // Load previous maps from Settings file
            LoadRecentItems();
            // Prepare Map Image settings
            mapImageFilter = new MapImageObjectFilter();

            // Keep up shortcut menus with current settings
            menuShowGrid.Checked = EditorSettings.Default.Draw_Grid;
            menuShowMinimap.Checked = EditorSettings.Default.Minimap_Show;
            menuVisualPreviewMode.Checked = EditorSettings.Default.Edit_PreviewMode;
            menuDrawTeleportPaths.Checked = EditorSettings.Default.Draw_Teleports;
            chkAutoIncrement.Checked = EditorSettings.Default.Save_AutoIncrement;

            LoadNewMap();
            if (args.Length > 0)
                if (File.Exists(args[0])) MapInterface.SwitchMap(args[0]);
            // Headless mode: MapEditor.exe <map> --render-image <out.png> [size]
            // renders the whole map like the Map Image tab, saves it and exits.
            if (args.Length >= 3 && args[1] == "--render-image")
            {
                Opacity = 0;
                ShowInTaskbar = false;
                // size "full:N" renders the whole 256x256 map uncropped at N pixels, so world positions
                // map to image positions exactly (N / 5880 image pixels per world pixel)
                string sizeArg = args.Length > 3 ? args[3] : "5880";
                bool full = sizeArg.StartsWith("full:");
                int size = int.Parse(full ? sizeArg.Substring(5) : sizeArg);
                Shown += (s, e) => RenderImageAndExit(args[2], size, full);
            }
            spl.Close();
        }

        private void MainWindow_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Delete)
            {
                mapView.DeleteSelectedObjects();
                Reload();

            }
        }
        private void MainWindow_Resize(object sender, EventArgs e)
        {
            mapView.MapRenderer.UpdateCanvas(true, true);
        }
        private void MainWindow_FormClosing(object sender, FormClosingEventArgs e)
        {
            EditorSettings.Default.Save();
            if (mapView.TimeManager.Count == 0)
                return;

            if (MessageBox.Show("Are you sure you wish to close?", "CLOSING EDITOR!", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) == DialogResult.Cancel)
                e.Cancel = true;
        }
        protected override void OnClosed(EventArgs e)
        {
            EditorSettings.Default.Reload(); // in case closed in Map Image tab
            EditorSettings.Default.IsMaximized = (WindowState == FormWindowState.Maximized);
            if (WindowState == FormWindowState.Normal)
                EditorSettings.Default.SaveSize = Size;
            EditorSettings.Default.Save();

            Logger.Close();
            Environment.Exit(0);
        }
        #endregion

        /* ####  MENUS  #### */
        #region File Menu
        private void menuNew_Click(object sender, EventArgs e)
        {
            LoadNewMap();
        }
        private void menuOpen_Click(object sender, EventArgs e)
        {
            OpenFileDialog fd = new OpenFileDialog
            {
                CheckFileExists = true,
                Filter = "Nox Map Files (*.map)|*.map|Compressed Map Files (*.nxz)|*.nxz"
            };

            if (fd.ShowDialog() == DialogResult.OK && File.Exists(fd.FileName))
                MapInterface.SwitchMap(fd.FileName);

        }
        private void menuRecent_DropDownItemClicked(object sender, ToolStripItemClickedEventArgs e)
        {
            if (e.ClickedItem.Text == map.FileName)
                return;

            if (File.Exists(e.ClickedItem.Text))
            {
                // No unsaved changes
                if (mapView.TimeManager.Count == 0)
                    MapInterface.SwitchMap(e.ClickedItem.Text);
                else    // Possible changes to current map, open new
                    Process.Start(Assembly.GetEntryAssembly().Location, e.ClickedItem.Text);
            }
        }
        private void menuInstallMap_Click(object sender, EventArgs e)
        {

            Saving saving = new Saving();
            string mapName = "";
            if (map.FileName != "" && map.FileName != null)
            {
                mapName = Path.GetFileName(map.FileName);
                string sub = mapName.Substring(0, mapName.Length - 4);
                mapName = sub;
            }
            saving.mapName.Text = mapName;

            if (saving.ShowDialog(this) == DialogResult.OK)
            {
                mapName = saving.mapName.Text;
            }
            else
                return;

            saving.Dispose();

            string mapDest = NoxDb.NoxPath + "Maps\\" + mapName;
            string newname = mapDest + "\\" + mapName + ".map";
            // MessageBox.Show(mapDest);
            if (!Directory.Exists(NoxDb.NoxPath + "Maps\\"))
            {
                MessageBox.Show("No permission to Nox map folder or that folder doesn't exist!");
                return;
            }
            else if (!File.Exists(newname))
            {
                try
                {
                    Directory.CreateDirectory(mapDest);
                    GrantAccess(mapDest);
                }
                catch
                {
                    MessageBox.Show("No permission to create folder!");
                    return;
                }
            }
            map.FileName = newname;
            SaveMap();


        }
        private void menuSave_Click(object sender, EventArgs e)
        {
            if (map == null)
                return;

            if (map.FileName == "" || map.FileName == null)
            {
                // Ask user to choose filename
                menuSaveAs.PerformClick();
                return;
            }

            StoreRecentItem(map.FileName);
            SaveMap();
            mapView.ShowMapStatus("MAP SAVED");
        }
        private void menuSaveAs_Click(object sender, EventArgs e)
        {
            SaveFileDialog fd = new SaveFileDialog();
            fd.Filter = "Nox Map Files (*.map)|*.map";

            if (fd.ShowDialog() == DialogResult.OK)
            {
                map.FileName = fd.FileName;
                menuSave.PerformClick();
            }
        }
        private void menuSaveNXZOnly_Click(object sender, EventArgs e)
        {
            map.ExtractNxz();
        }
        private void menuImportSave_Click(object sender, EventArgs e)
        {
            if (scriptPath == "")
                return;
            if (File.Exists(scriptPath))
            {
                NoxBinaryReader rdr = new NoxBinaryReader(File.Open(scriptPath, FileMode.Open), CryptApi.NoxCryptFormat.NONE);
                map.ReadScriptObject(rdr);
            }

            menuSave.PerformClick();
        }
        private void menuImportScript_Click(object sender, EventArgs e)
        {
            OpenFileDialog fd = new OpenFileDialog();
            fd.Filter = "Nox Script Objects (*.obj)|*.obj";
            fd.DefaultExt = ".obj";
            if (!string.IsNullOrEmpty(map.FileName))
            {
                fd.FileName = Path.GetFileNameWithoutExtension(map.FileName) + ".obj";
                fd.InitialDirectory = Path.GetDirectoryName(map.FileName);
            }

            if (fd.ShowDialog() == DialogResult.OK)
            {
                NoxBinaryReader rdr = new NoxBinaryReader(File.Open(fd.FileName, FileMode.Open), CryptApi.NoxCryptFormat.NONE);
                map.ReadScriptObject(rdr);
                scriptPath = fd.FileName;
                menuImportSave.Enabled = true;
                rdr.Close();
            }
        }
        private void menuExportScript_Click(object sender, EventArgs evt)
        {
            SaveFileDialog fd = new SaveFileDialog();
            fd.Filter = "Nox Script Source (*.ns)|*.ns";
            fd.DefaultExt = ".ns";
            if (!string.IsNullOrEmpty(map.FileName))
            {
                fd.FileName = Path.GetFileNameWithoutExtension(map.FileName);
                fd.InitialDirectory = Path.GetDirectoryName(map.FileName);
            }

            if (map.Scripts.SctStr.Count > 0 && map.Scripts.SctStr[0].StartsWith("NOXSCRIPT3.0"))
            {
                if (map.Scripts.SctStr[0].Length <= 12)
                {
                    // Full script NOT stored in first element
                    MessageBox.Show("Using Nox Script 3.0 but script was not preserved. Unknown compiler.", "Error");
                    return;
                }

                // we already have script code, just save it
                if (fd.ShowDialog() == DialogResult.OK)
                    File.WriteAllText(fd.FileName, map.Scripts.SctStr[0].Substring(12));
            }
            else
            {
                if (nsdc != null)
                {
                    MessageBox.Show("Decompiler is running. Please wait and try again.");
                    return;
                }

                var dr = MessageBox.Show("Nox Script 3.0 not found, attempt decompile?", "Warning", MessageBoxButtons.OKCancel, MessageBoxIcon.Warning);
                if (dr == DialogResult.Cancel)
                    return;

                string tmp = Path.GetTempFileName();
                NoxBinaryWriter wtr = new NoxBinaryWriter(new FileStream(tmp, FileMode.Create), CryptApi.NoxCryptFormat.NONE);
                map.WriteScriptObject(wtr);
                wtr.Close();

                string tmp2 = Path.GetTempFileName();
                Func<string, string> escape = (string s) =>
                {
                    return "\"" + System.Text.RegularExpressions.Regex.Replace(s, @"(\\+)$", @"$1$1") + "\"";
                };
                nsdc = new Process();
                nsdc.StartInfo.WorkingDirectory = Path.Combine(Application.StartupPath, "noxscript");
                nsdc.StartInfo.FileName = Path.Combine(nsdc.StartInfo.WorkingDirectory, "nsdc.exe");
                nsdc.StartInfo.Arguments = string.Format("-o {0} {1}", escape(tmp2), escape(tmp));
                nsdc.StartInfo.RedirectStandardError = true;
                nsdc.StartInfo.RedirectStandardOutput = true;
                nsdc.StartInfo.UseShellExecute = false;
                nsdc.EnableRaisingEvents = true;
                nsdc.Exited += (sender_, args) =>
                {
                    BeginInvoke((Action)delegate ()
                    {
                        try
                        {
                            var stdErr = nsdc.StandardError.ReadToEnd();
                            var stdOut = nsdc.StandardOutput.ReadToEnd();

                            if (((stdErr != null) && (stdErr != ""))
                            && ((stdOut == null) || (stdOut == "")))
                                MessageBox.Show(stdErr, "Failed to decompile", MessageBoxButtons.OK, MessageBoxIcon.Warning);

                            else
                            {
                                if (fd.ShowDialog() == DialogResult.OK)
                                {
                                    File.Delete(fd.FileName);
                                    File.Copy(tmp2, fd.FileName);
                                    StreamWriter sw = new StreamWriter(fd.FileName, true);

                                    if (stdErr != null)
                                        sw.Write("// " + stdErr.Replace("\n", "\n// "));
                                    if (stdOut != null)
                                        sw.Write("// " + stdOut.Replace("\n", "\n// "));

                                    sw.Close();
                                }
                            }
                        }
                        catch (Exception e) { MessageBox.Show("Error trying to run decompiler: " + e.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error); }
                        finally
                        {
                            File.Delete(tmp);
                            File.Delete(tmp2);
                            nsdc.Dispose();
                            nsdc = null;
                        }

                    });
                };
                try
                {
                    nsdc.Start();
                }
                catch (System.ComponentModel.Win32Exception e)
                {
                    MessageBox.Show("Error trying to run decompiler: " + e.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    File.Delete(tmp);
                    File.Delete(tmp2);
                    nsdc.Dispose();
                }
                return;
            }
        }
        private void menuExportNativeScript_Click(object sender, EventArgs e)
        {
            var sfd = new SaveFileDialog()
            {
                DefaultExt = ".txt",
                Filter = "Text Files (*.txt)|*.txt|All Files (*.*)|*.*"
            };
            if (!string.IsNullOrEmpty(map.FileName))
            {
                sfd.FileName = Path.GetFileNameWithoutExtension(map.FileName);
                sfd.InitialDirectory = Path.GetDirectoryName(map.FileName);
            }

            var scriptDialog = new ScriptFunctionDialog();
            scriptDialog.Scripts = map.Scripts;
            if (sfd.ShowDialog() == DialogResult.OK)
                File.WriteAllText(sfd.FileName, scriptDialog.ExportNativeScript());
        }
        private void menuExit_Click(object sender, EventArgs e)
        {
            Close();
        }
        #endregion
        #region Map Menu
        private void menuListObjects_Click(object sender, EventArgs e)
        {
            ObjectListDialog objLd = new ObjectListDialog();
            objLd.objTable = map.Objects;
            objLd.objTable2 = map.Objects;
            objLd.Map = mapView;
            var dr = objLd.ShowDialog();
            objLd.Owner = this;

            // Apply changes
            if (dr == DialogResult.OK)
            {
                if (objLd.Result != null)
                {
                    map.Objects = objLd.Result;
                    MainWindow_Resize(sender, e);
                }
            }
        }
        private void menuScripts_Click(object sender, EventArgs e)
        {
            mapView.OpenScripts();
        }
        private void menuGroups_Click(object sender, EventArgs e)
        {
            GroupDialog gd = new GroupDialog(map.Groups);
            gd.Show();
        }
        private void menuPolygons_Click(object sender, EventArgs e)
        {
            PolygonEditor editor = mapView.PolygonEditDlg;
            //  MapInterface.CurrentMode = MapInt.EditMode.POLYGON_RESHAPE;
            editor.Show();

            if (panelTabs.SelectedIndex == 1)
            {
                Point po = new Point(miniViewPanel.Width, 0);
                po = miniViewPanel.PointToScreen(po);
                if (!IsOnScreen(new Point(po.X + mapView.PolygonEditDlg.Width, po.Y))) return;
                editor.Location = po;
                miniEdit.Checked = true;
            }
        }
        private void menuWaypoints_Click(object sender, EventArgs e)
        {
            WaypointListDialog waypointListDialog = new WaypointListDialog();
            waypointListDialog.WpsTable = map.Waypoints;
            waypointListDialog.Map = mapView;
            waypointListDialog.ShowDialog();
        }
        private void menuFixExtents_Click(object sender, EventArgs e)
        {
            var dupesFound = MapInterface.FixObjectExtents();
            if (dupesFound <= 0)
            {
                MessageBox.Show("No duplicated extents found.");
            }
            else
            {
                mapView.MapRenderer.UpdateCanvas(true, false, true);
                MessageBox.Show(dupesFound + " duplicated extents have been fixed.");
            }
        }
        private void menuMapGenerator_Click(object sender, EventArgs e)
        {
            var dr = new MapGeneratorDlg(mapView).ShowDialog();
            if (dr == DialogResult.Abort)
                menuNew.PerformClick();
            Reload();
        }
        #endregion
        #region Options Menu
        private void menuShowGrid_Click(object sender, EventArgs e)
        {
            bool check = !menuShowGrid.Checked;
            menuShowGrid.Checked = check;
            // Update settings
            EditorSettings.Default.Draw_Grid = check;
            EditorSettings.Default.Save();
        }
        private void menuShowMinimap_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Minimap_Show = !EditorSettings.Default.Minimap_Show;
            menuShowMinimap.Checked = !menuShowMinimap.Checked;
            if (minimap.Visible)
            {
                minimap.Hide();
            }
            else
            {
                minimap.Show(this);
                minimap.setPos();
            }
        }
        private void menuVisualPreviewMode_Click(object sender, EventArgs e)
        {
            bool check = !menuVisualPreviewMode.Checked;
            menuVisualPreviewMode.Checked = check;

            // Update settings
            EditorSettings.Default.Edit_PreviewMode = check;
            EditorSettings.Default.Save();
            mapView.MapRenderer.UpdateCanvas(true, true);
            mapView.cmdQuickPreview.Checked = check;
            Invalidate(true);

        }
        private void menuInvertColors_Click(object sender, EventArgs e)
        {
            menuInvertColors.Checked = !menuInvertColors.Checked;
            if (menuInvertColors.Checked)
                mapView.MapRenderer.ColorLayout.InvertColors();
            else
                mapView.MapRenderer.ColorLayout.ResetColors();
        }
        private void menuSettings_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Save();
            SettingsDialog settings = new SettingsDialog();
            settings.ShowDialog(this);
        }
        #endregion
        #region Help Menu
        private void menuHelpLink1_Click(object sender, EventArgs e)
        {
            Process.Start("http://www.noxcommunity.com/forum/");
        }
        private void menuHelpLink2_Click(object sender, EventArgs e)
        {
            Process.Start("http://bit.ly/noxdiscord");
        }
        private void menuHelpLink3_Click(object sender, EventArgs e)
        {
            Process.Start("https://nox.fandom.com/wiki/Game_texts");
        }
        private void menuHelpLink4_Click(object sender, EventArgs e)
        {
            Process.Start("https://noxtools.github.io/noxscript/builtins_8h.html");
        }
        private void menuHelpLink5_Click(object sender, EventArgs e)
        {
            Process.Start("https://nox.fandom.com/wiki/Map_Editor_Scripting");
        }
        private void menuAbout_Click(object sender, EventArgs e)
        {
            AboutDialog dlg = new AboutDialog();
            dlg.ShowDialog();
        }
        #endregion
        #region Shortcuts Menu (hidden)
        private void menuPicker_Click(object sender, EventArgs e)
        {
            mapView.Picker.Checked = !mapView.Picker.Checked;
        }
        private void menuUndo_Click(object sender, EventArgs e)
        {
            mapView.cmdUndo.PerformClick();
        }
        private void menuRedo_Click(object sender, EventArgs e)
        {
            mapView.cmdRedo.PerformClick();
        }
        private void menuRectangleDraw_Click(object sender, EventArgs e)
        {
            if (MapInterface.CurrentMode != EditMode.WALL_BRUSH)
                return;
            mapView.WallMakeNewCtrl.RecWall.Checked = !mapView.WallMakeNewCtrl.RecWall.Checked;
            mapView.WallMakeNewCtrl.LineWall.Checked = false;
        }
        private void menuLineDraw_Click(object sender, EventArgs e)
        {
            if (MapInterface.CurrentMode != EditMode.WALL_BRUSH)
                return;
            mapView.WallMakeNewCtrl.LineWall.Checked = !mapView.WallMakeNewCtrl.LineWall.Checked;
            mapView.WallMakeNewCtrl.RecWall.Checked = false;
        }
        private void menuDrawObjects_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Draw_Objects = !EditorSettings.Default.Draw_Objects;
            mapView.mapPanel.Invalidate();
        }
        private void menuDrawWalls_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Draw_Walls = !EditorSettings.Default.Draw_Walls;
            mapView.mapPanel.Invalidate();
        }
        private void menuRotateSelection45_Click(object sender, EventArgs e)
        {
            mapView.Switch45Area();
        }
        private void menuDraw3DExtents_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Draw_Extents_3D = !EditorSettings.Default.Draw_Extents_3D;
            EditorSettings.Default.Draw_AllExtents = EditorSettings.Default.Draw_Extents_3D;
            mapView.SetRadioDraw();
            mapView.mapPanel.Invalidate();
        }
        private void menuDrawTeleportPaths_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Draw_Teleports = !EditorSettings.Default.Draw_Teleports;
            menuDrawTeleportPaths.Checked = !menuDrawTeleportPaths.Checked;
            mapView.mapPanel.Invalidate();
        }
        private void menuDrawWaypoints_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Draw_Waypoints = !EditorSettings.Default.Draw_Waypoints;
            menuDrawWaypoints.Checked = !menuDrawWaypoints.Checked;
            mapView.mapPanel.Invalidate();
        }
        private void menuColorSpecialWalls_Click(object sender, EventArgs e)
        {
            EditorSettings.Default.Draw_ColorWalls = !EditorSettings.Default.Draw_ColorWalls;
            mapView.mapPanel.Invalidate();
        }
        #endregion
        #region Object Search
        private void suggestBox_MouseClick(object sender, MouseEventArgs e)
        {
            mapView.cboObjCreate.Text = suggestBox.SelectedItem.ToString();
            if (!MapInterface.KeyHelper.ShiftKey)
                suggestBox.Visible = false;
            else
                suggestBlocked = true;
        }
        private void suggestBox_MouseMove(object sender, MouseEventArgs e)
        {
            mapView.mapPanel.Invalidate();
            if (suggestBlocked)
                return;
            int itemHeight = suggestBox.ItemHeight;
            int num1 = suggestBox.TopIndex * itemHeight;
            int num2 = (e.Y + num1) / itemHeight;
            if (num2 >= suggestBox.Items.Count)
                return;
            suggestBox.SelectedIndex = num2;
            string index = suggestBox.SelectedItem.ToString();
            ThingDb.Thing thing = ThingDb.Things[index];
            Bitmap bitmap = null;
            if (thing.SpritePrettyImage > 0 && (thing.Class & ThingDb.Thing.ClassFlags.MONSTER) == ThingDb.Thing.ClassFlags.NULL)
                bitmap = mapView.MapRenderer.VideoBag.GetBitmap(thing.SpritePrettyImage);
            else if (thing.SpriteMenuIcon > 0)
            {
                bitmap = mapView.MapRenderer.VideoBag.GetBitmap(thing.SpriteMenuIcon);
                if (thing.Xfer != "InvisibleLightXfer" && !thing.Name.StartsWith("Amb") && thing.SpriteAnimFrames.Count > 0)
                    bitmap = mapView.MapRenderer.VideoBag.GetBitmap(thing.SpriteAnimFrames[thing.SpriteAnimFrames.Count - 1]);
            }
            mapView.objectPreview.BackgroundImage = (Image)bitmap;
        }
        private void suggestBox_MouseEnter(object sender, EventArgs e)
        {
            suggestBox.Focus();
        }
        private void suggestBox_MouseLeave(object sender, EventArgs e)
        {
            ThingDb.Thing thing1 = ThingDb.GetThing(mapView.cboObjCreate.Text);
            if (thing1 == null)
                return;
            ThingDb.Thing thing2 = ThingDb.Things[thing1.Name];
            Bitmap bitmap = null;
            if (thing2.SpritePrettyImage > 0 && (thing2.Class & ThingDb.Thing.ClassFlags.MONSTER) == ThingDb.Thing.ClassFlags.NULL)
                bitmap = mapView.MapRenderer.VideoBag.GetBitmap(thing2.SpritePrettyImage);
            else if (thing2.SpriteMenuIcon > 0)
            {
                bitmap = mapView.MapRenderer.VideoBag.GetBitmap(thing2.SpriteMenuIcon);
                if (thing2.Xfer != "InvisibleLightXfer" && !thing2.Name.StartsWith("Amb") && thing2.SpriteAnimFrames.Count > 0)
                    bitmap = mapView.MapRenderer.VideoBag.GetBitmap(thing2.SpriteAnimFrames[thing2.SpriteAnimFrames.Count - 1]);
            }
            mapView.objectPreview.BackgroundImage = bitmap;
        }
        #endregion

        /* ####  TABS  #### */
        private void panelTabs_MouseClick(object sender, MouseEventArgs e)
        {
            var page = panelTabs.SelectedTab;

            if (page == largeMap)
            {
                mapView.MapRenderer.UpdateCanvas(true, true);
                mapView.TabMapToolsSelectedIndexChanged(sender, e);

                if (EditorSettings.Default.Minimap_Show)
                {
                    minimap.Visible = true;
                    minimap.Reload();
                    minimap.setPos();
                    minimap.Invalidate();
                }
            }
            else { minimap.Hide(); }
            mapView.mapPanel.Invalidate();

            if (page == minimapTab)
            {
                miniUndo.Enabled = mapView.cmdUndo.Enabled;
                miniRedo.Enabled = mapView.cmdRedo.Enabled;

                if (miniWallBrush.Checked)
                    miniLineWall.Visible = true;
                else
                    miniLineWall.Visible = false;

                RestrictWallTilesOnly();

                if (MapInterface.CurrentMode == EditMode.FLOOR_PLACE || MapInterface.CurrentMode == EditMode.FLOOR_BRUSH)
                {
                    miniTilePLace.Checked = mapView.TileMakeNewCtrl.PlaceTileBtn.Checked;
                    miniTileBrush.Checked = mapView.TileMakeNewCtrl.AutoTileBtn.Checked;
                }

                if (MapInterface.CurrentMode == EditMode.WALL_BRUSH || MapInterface.CurrentMode == EditMode.WALL_PLACE)
                    miniWallBrush.Checked = true;
                lastMapImage = null;
                Invalidate(true);
                numBrushSize.Value = mapView.TileMakeNewCtrl.BrushSize.Value;
                if (MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE || mapView.PolygonEditDlg.Visible)
                {
                    miniEdit.Checked = true;
                    Point po = new Point(miniViewPanel.Width, 0);
                    po = miniViewPanel.PointToScreen(po);
                    if (!IsOnScreen(new Point(po.X + mapView.PolygonEditDlg.Width, po.Y))) return;
                    mapView.PolygonEditDlg.Location = po;
                    miniEdit.Checked = true;
                    return;
                }
                if (miniTilePLace.Checked)
                    MapInterface.CurrentMode = EditMode.FLOOR_PLACE;
                else if (miniTileBrush.Checked)
                    MapInterface.CurrentMode = EditMode.FLOOR_BRUSH;
                else if (miniWallBrush.Checked)
                    MapInterface.CurrentMode = EditMode.WALL_BRUSH;
            }

            if (page != mapImageTab)
            {
                imgMode = false;
                EditorSettings.Default.Reload();
            }
        }

        #region Mini Map Tab
        private void numMinimapZoom_ValueChanged(object sender, EventArgs e)
        {
            mapZoom = (int)numMinimapZoom.Value;
            lastMapImage = null;
            Invalidate(true);
        }
        private void numBrushSize_ValueChanged(object sender, EventArgs e)
        {
            mapView.TileMakeNewCtrl.BrushSize.Value = numBrushSize.Value;
        }

        private void panelInnerMinimap_Scroll(object sender, ScrollEventArgs e)
        {
            //  redraw = new Rectangle(new Point(-500, -500), new Size(0,0));
            if (e.Type == ScrollEventType.ThumbPosition)
            {
                //redraw = new Rectangle(new Point(0, 0), new Size(200, 200));
                lastMapImage = null;
                Invalidate(true);
            }

        }
        private void panelInnerMinimap_MouseUp(object sender, MouseEventArgs e)
        {
            RightDown = false;
        }

        private void miniViewPanel_Paint(object sender, PaintEventArgs e)
        {
            if (map == null) return;

            Pen pen;
            redraw = new Rectangle(new Point(((mouseLocation.X - 34)), ((mouseLocation.Y - 34))), new Size(68, 68));
            Graphics graphics = e.Graphics;
            graphics.CompositingQuality = CompositingQuality.HighSpeed;
            graphics.CompositingMode = CompositingMode.SourceCopy;

            //graphics.Clear(Color.Black);

            // обновляем размер миникарт?
            miniViewPanel.Width = mapDimension * mapZoom;
            miniViewPanel.Height = mapDimension * mapZoom;
            // отрисовк?
            Bitmap newMap;
            if (lastMapImage != null)
                newMap = lastMapImage;
            else
            {
                redraw = new Rectangle(new Point(0, 0), new Size(miniViewPanel.Width, miniViewPanel.Height));
                newMap = new Bitmap(miniViewPanel.Width, miniViewPanel.Height);
            }

            MinimapRenderer minimap = new MinimapRenderer(newMap, map, mapView.MapRenderer.FakeWalls);
            minimap.LockBitmap();
            minimap.DrawMinimap(mapZoom, redraw);
            newMap = minimap.UnlockBitmap();

            if (MapInterface.CurrentMode != EditMode.POLYGON_RESHAPE)
                lastMapImage = newMap;
            graphics.DrawImage(newMap, 0, 0, newMap.Width, newMap.Height);

            // лини?деления
            if (chkDivide.Checked)
                graphics.DrawLine(new Pen(Color.Aqua, 1), new Point(0, 0), new Point(miniViewPanel.Width, miniViewPanel.Height));
            if (chkDivide2.Checked)
                graphics.DrawLine(new Pen(Color.Aqua, 1), new Point(miniViewPanel.Width, 0), new Point(0, miniViewPanel.Height));

            if (EditorSettings.Default.Draw_Polygons)
            {

                foreach (Map.Polygon poly in map.Polygons)
                {
                    List<PointF> points = new List<PointF>();
                    pen = Pens.PaleGreen;

                    foreach (PointF pt in poly.Points)
                    {
                        float pointX = (pt.X / MapView.squareSize) * mapZoom;
                        float pointY = (pt.Y / MapView.squareSize) * mapZoom;
                        PointF center = new PointF(pointX, pointY);

                        Pen pen2 = MapInterface.SelectedPolyPoint == pt ? Pens.DodgerBlue : Pens.DeepPink;
                        if (mapView.PolygonEditDlg.SelectedPolygon == poly && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE)
                        {
                            PointF centered = new PointF(center.X - 4, center.Y - 4);
                            pen = Pens.PaleVioletRed;
                            graphics.DrawEllipse(pen2, new RectangleF(centered, new Size(2 * 4, 2 * 4)));

                        }
                        points.Add(center);
                    }
                    if (poly.Points.Count > 2)
                    {

                        if (mapView.PolygonEditDlg.SuperPolygon == poly && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE)
                            pen = new Pen(Color.PaleVioletRed, 2);

                        graphics.DrawLines(pen, points.ToArray());
                        graphics.DrawLine(pen, points[points.Count - 1], points[0]);
                    }
                }
            }
        }
        private void miniViewPanel_MouseDown(object sender, MouseEventArgs e)
        {
            if (!miniEdit.Checked)
            {
                mapView.CenterAtPoint(new Point(e.X / mapZoom * MapView.squareSize, e.Y / mapZoom * MapView.squareSize));
                panelTabs.SelectTab("largeMap");
                mapView.TabMapToolsSelectedIndexChanged(sender, e);
                minimap.applySettings();
                minimap.setPos();
                minimap.Reload();
            }
            else if (MapInterface.CurrentMode != EditMode.WALL_BRUSH && MapInterface.CurrentMode != EditMode.FLOOR_BRUSH && (MapInterface.CurrentMode != EditMode.FLOOR_PLACE && MapInterface.CurrentMode != EditMode.POLYGON_RESHAPE))
            {
                MessageBox.Show("MiniMap Mode supports only Wall, Tile, and Polygon operations!");
            }
            else
            {
                mapView.BlockTime = true;
                if (!mapView.done)
                    return;

                mouseLocation = new Point(e.X, e.Y);
                if (!miniEdit.Checked)
                    return;

                Rectangle redraw = new Rectangle(new Point(e.X + 103 + miniViewPanel.Left, e.Y - 4 + miniViewPanel.Top), new Size(50, 50));
                Rectangle minimapBounds = new Rectangle(new Point(0, 0), new Size(mapDimension * mapZoom, mapDimension * mapZoom));
                if (minimapBounds.Contains(e.X, e.Y))
                {
                    Point pt = new Point((e.X * 2) * MapView.squareSize / (mapZoom * 2), (e.Y * 2) * MapView.squareSize / (mapZoom * 2));
                    added = false;


                    if (MapInterface.CurrentMode == EditMode.FLOOR_BRUSH || MapInterface.CurrentMode == EditMode.FLOOR_PLACE || (MapInterface.CurrentMode == EditMode.WALL_BRUSH || MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE))
                    {
                        if (e.Button.Equals(MouseButtons.Left))
                        {
                            mapView.mouseKeep = pt;
                            if (MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE && MapInterface.KeyHelper.ShiftKey)
                                added = mapView.ApplyStore();
                            else if (MapInterface.CurrentMode != EditMode.POLYGON_RESHAPE)
                                added = mapView.ApplyStore();


                        }
                        else if (e.Button.Equals(MouseButtons.Right))
                        {
                            if (MapInterface.CurrentMode == EditMode.FLOOR_BRUSH || MapInterface.CurrentMode == EditMode.FLOOR_PLACE || MapInterface.CurrentMode == EditMode.WALL_BRUSH)
                                added = mapView.ApplyStore();

                        }
                    }

                    if (MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE)
                    {
                        if (e.Button == MouseButtons.Left)
                        {

                            if (mapView.PolygonEditDlg.SelectedPolygon != null)
                            {
                                if (MapInterface.KeyHelper.ShiftKey)
                                {
                                    mapView.PolygonEditDlg.SelectedPolygon.Points.Insert(mapView.arrowPoly, pt);
                                    if (mapView.PolygonEditDlg.SelectedPolygon.Points.Count > 2)
                                        MapInterface.OpUpdatedPolygons = true;
                                }
                                else
                                    mapView.arrowPoly = MapInterface.PolyPointSelect(pt);

                                Invalidate(true);
                            }

                            if (mapView.PolygonEditDlg.SelectedPolygon != null && !MapInterface.KeyHelper.ShiftKey)
                            {
                                if (MapInterface.SelectedPolyPoint.IsEmpty && mapView.PolygonEditDlg.SelectedPolygon.Points.Count > 2)
                                {
                                    if (mapView.PolygonEditDlg.SelectedPolygon == mapView.PolygonEditDlg.SuperPolygon && mapView.PolygonEditDlg.SelectedPolygon != null && !mapView.PolygonEditDlg.LockedBox.Checked && !mapView.PolygonEditDlg.SelectedPolygon.IsPointInside(pt))
                                        mapView.PolygonEditDlg.SuperPolygon = null;
                                    else if (mapView.PolygonEditDlg.Visible && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE && mapView.PolygonEditDlg.SelectedPolygon != null && mapView.PolygonEditDlg.SelectedPolygon.IsPointInside(pt))
                                        mapView.PolygonEditDlg.SuperPolygon = mapView.PolygonEditDlg.SelectedPolygon;
                                    else if (mapView.PolygonEditDlg.SuperPolygon != mapView.PolygonEditDlg.SelectedPolygon)
                                        mapView.PolygonEditDlg.SelectedPolygon = null;
                                }
                            }
                        }
                    }
                    else if (e.Button == MouseButtons.Left)
                        MapInterface.HandleLMouseClick(pt);
                    else if (e.Button == MouseButtons.Right)
                    {
                        MapInterface.HandleRMouseClick(pt);
                        Invalidate(redraw, true);
                    }
                }
                moved = false;
            }
        }
        private void miniViewPanel_MouseDoubleClick(object sender, MouseEventArgs e)
        {
            if (mapView.PolygonEditDlg.Visible && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE && mapView.PolygonEditDlg.SelectedPolygon != null && mapView.PolygonEditDlg.SelectedPolygon.Points.Count > 2)
            {
                Point pt = new Point((e.X * 2) * MapView.squareSize / (mapZoom * 2), (e.Y * 2) * MapView.squareSize / (mapZoom * 2));
                if (mapView.PolygonEditDlg.SelectedPolygon.IsPointInside(pt))
                    mapView.PolygonEditDlg.ButtonModifyClick(sender, e);
            }
        }
        private void miniViewPanel_MouseUp(object sender, MouseEventArgs e)
        {
            mapView.mouseMove = false;
            if (MapInterface.CurrentMode != EditMode.WALL_BRUSH && MapInterface.CurrentMode != EditMode.FLOOR_BRUSH && (MapInterface.CurrentMode != EditMode.FLOOR_PLACE && MapInterface.CurrentMode != EditMode.POLYGON_RESHAPE))
                return;
            Point mouseKeep = mapView.mouseKeep;
            RightDown = false;
            lastMapImage = null;
            if (!mouseKeep.IsEmpty)
            {
                mapView.mouseKeepOff = mapView.mouseKeep;
                mapView.mouseKeep = new Point();
            }
            if (!MapInterface.OpUpdatedTiles && !MapInterface.OpUpdatedWalls && (!MapInterface.OpUpdatedPolygons && added) && (!moved && (MapInterface.CurrentMode != EditMode.WALL_BRUSH || !miniLineWall.Checked)))
            {
                while (mapView.TimeManager.Count > 0 && mapView.TimeManager[mapView.TimeManager.Count - 1 - mapView.currentStep].Event == MapView.TimeEvent.PRE)
                {
                    if (mapView.TimeManager[mapView.TimeManager.Count - 1 - mapView.currentStep].Event == MapView.TimeEvent.PRE && mapView.TimeManager.Count > 0)
                        mapView.TimeManager.RemoveAt(mapView.TimeManager.Count - 1 - mapView.currentStep);
                }
                if (mapView.TimeManager.Count <= 1)
                {
                    MainWindow.Instance.miniUndo.Enabled = false;
                    miniUndo.Enabled = false;
                }
            }
            if (mapView.WallMakeNewCtrl.LineWall.Checked || mapView.WallMakeNewCtrl.RecWall.Checked)
                mapView.LastWalls.Clear();
            if (MapInterface.OpUpdatedTiles || MapInterface.OpUpdatedWalls || (MapInterface.OpUpdatedPolygons || moved))
            {
                switch (MapInterface.CurrentMode)
                {
                    case EditMode.WALL_PLACE:
                    case EditMode.WALL_BRUSH:
                    case EditMode.WALL_CHANGE:
                    case EditMode.FLOOR_PLACE:
                    case EditMode.FLOOR_BRUSH:
                    case EditMode.EDGE_PLACE:
                    case EditMode.OBJECT_PLACE:
                    case EditMode.OBJECT_SELECT:
                    case EditMode.POLYGON_RESHAPE:
                        if (!miniLineWall.Checked || MapInterface.CurrentMode != EditMode.WALL_BRUSH)
                        {
                            if (MapInterface.CurrentMode >= EditMode.WALL_PLACE && MapInterface.CurrentMode < EditMode.OBJECT_PLACE && (MapInterface.OpUpdatedTiles || MapInterface.OpUpdatedWalls || MapInterface.OpUpdatedPolygons))
                                mapView.Store(MapInterface.CurrentMode, MapView.TimeEvent.POST);
                            if ((!MapInterface.SelectedPolyPoint.IsEmpty || mapView.PolygonEditDlg.SuperPolygon != null) && (!MapInterface.KeyHelper.ShiftKey && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE) && (moved || MapInterface.OpUpdatedPolygons))
                            {
                                mapView.Store(MapInterface.CurrentMode, MapView.TimeEvent.POST);
                                break;
                            }
                            if (MapInterface.KeyHelper.ShiftKey && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE)
                            {
                                mapView.Store(MapInterface.CurrentMode, MapView.TimeEvent.POST);
                                break;
                            }
                            break;
                        }
                        break;
                }
            }
            mapView.BlockTime = false;
            moved = false;
            MapInterface.ResetUpdateTracker();
            Invalidate(true);
        }
        private void miniViewPanel_MouseMove(object sender, MouseEventArgs e)
        {
            if (!mapView.done)
                return;
            mouseLocation = new Point(e.X, e.Y);
            if (mapView.PolygonEditDlg.Visible)
            {
                Point screen = mapView.PolygonEditDlg.PointToScreen(mouseLocation);
                if (mapView.PolygonEditDlg.ClientRectangle.Contains(MainWindow.Instance.PointToClient(screen)))
                    return;
                MainWindow.Instance.Focus();
            }
            if (MapInterface.CurrentMode != EditMode.WALL_BRUSH && MapInterface.CurrentMode != EditMode.FLOOR_BRUSH && (MapInterface.CurrentMode != EditMode.FLOOR_PLACE && MapInterface.CurrentMode != EditMode.POLYGON_RESHAPE))
                return;
            Point mouseKeep = mapView.mouseKeep;
            if (!miniEdit.Checked)
                return;
            Rectangle rectangle1 = new Rectangle(new Point(0, 0), new Size(mapDimension * mapZoom, mapDimension * mapZoom));
            Rectangle rc = new Rectangle(new Point(e.X + 100 + miniViewPanel.Left, e.Y - 8 + miniViewPanel.Top), new Size(60, 60));
            if (rectangle1.Contains(e.X, e.Y))
            {
                if (!e.Button.Equals((object)MouseButtons.Left))
                {
                    mapView.mouseMove = true;
                    if (!mouseKeep.IsEmpty)
                    {
                        mapView.mouseKeepOff = mapView.mouseKeep;
                        mapView.mouseKeep = new Point();
                    }
                    if (MainWindow.Instance.mapView.PolygonEditDlg.Visible && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE && !mapView.PolygonEditDlg.LockedBox.Checked && (MainWindow.Instance.mapView.PolygonEditDlg.SelectedPolygon == null || mapView.PolygonEditDlg.SelectedPolygon != mapView.PolygonEditDlg.SuperPolygon))
                    {
                        int num = -1;
                        foreach (Map.Polygon polygon in (ArrayList)map.Polygons)
                        {
                            ++num;
                            List<Point> pointList = new List<Point>();
                            foreach (PointF point1 in polygon.Points)
                            {
                                Point point2 = new Point((int)(point1.X / MapView.squareSize * (float)mapZoom), (int)(point1.Y / MapView.squareSize * (float)mapZoom));
                                pointList.Add(point2);
                            }
                            if (MapInterface.PointInPolygon(mouseLocation, pointList.ToArray()))
                            {
                                MainWindow.Instance.mapView.PolygonEditDlg.listBoxPolygons.SelectedIndex = num;
                                MainWindow.Instance.mapView.PolygonEditDlg.SelectedPolygon = polygon;
                                break;
                            }
                        }
                    }
                }
                if (miniLineWall.Checked && MapInterface.CurrentMode == EditMode.WALL_BRUSH)
                {
                    MapInterface.WallLine(new Point(e.X * 2 * MapView.squareSize / (mapZoom * 2), e.Y * 2 * MapView.squareSize / (mapZoom * 2)), false, new Point(), true);
                    lastMapImage = null;
                    Invalidate(true);
                }
                if (e.Button == MouseButtons.Left)
                {
                    if (MapInterface.CurrentMode != EditMode.WALL_BRUSH && MapInterface.CurrentMode != EditMode.FLOOR_BRUSH && (MapInterface.CurrentMode != EditMode.FLOOR_PLACE && MapInterface.CurrentMode != EditMode.POLYGON_RESHAPE))
                    {
                        int num = (int)MessageBox.Show("MiniMap Mode supports only Wall, Tile, and Polygon operations!");
                        return;
                    }
                    Point pt = new Point(e.X * 2 * MapView.squareSize / (mapZoom * 2), e.Y * 2 * MapView.squareSize / (mapZoom * 2));
                    if (!mouseKeep.IsEmpty && (!MapInterface.SelectedPolyPoint.IsEmpty || mapView.PolygonEditDlg.SuperPolygon != null) && MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE)
                    {
                        if (mapView.PolygonEditDlg.SuperPolygon != null)
                        {
                            if (mapView.PolygonEditDlg.SuperPolygon.IsPointInside((PointF)pt))
                            {
                                mapView.ApplyStore();
                                moved = true;
                            }
                            else if (!MapInterface.SelectedPolyPoint.IsEmpty)
                            {
                                mapView.ApplyStore();
                                moved = true;
                            }
                        }
                        else if (!MapInterface.SelectedPolyPoint.IsEmpty)
                        {
                            mapView.ApplyStore();
                            moved = true;
                        }
                    }
                    if (MapInterface.CurrentMode == EditMode.POLYGON_RESHAPE)
                    {
                        Rectangle rectangle2 = new Rectangle(new Point(3, 3), new Size(miniViewPanel.Width - 6, miniViewPanel.Height - 6));
                        if (!MapInterface.SelectedPolyPoint.IsEmpty && !MapInterface.KeyHelper.ShiftKey && rectangle2.Contains(e.Location))
                        {
                            PointF pointF = pt;
                            if (mapView.PolygonEditDlg.snapPoly.Checked)
                                pointF = MapInterface.PolyPointSnap(mouseLocation).IsEmpty ? (PointF)pt : MapInterface.PolyPointSnap(mouseLocation);
                            mapView.PolygonEditDlg.SelectedPolygon.Points[mapView.arrowPoly] = pointF;
                            MapInterface.SelectedPolyPoint = pointF;
                            Invalidate(true);
                        }
                        if (mapView.PolygonEditDlg.SuperPolygon != null && MapInterface.SelectedPolyPoint.IsEmpty && mapView.PolygonEditDlg.SuperPolygon.IsPointInside((PointF)pt))
                        {
                            for (int index = 0; index < mapView.PolygonEditDlg.SuperPolygon.Points.Count; ++index)
                            {
                                PointF point = mapView.PolygonEditDlg.SuperPolygon.Points[index];
                                if (mapView.PolyPointOffset.Count <= mapView.PolygonEditDlg.SuperPolygon.Points.Count)
                                    mapView.PolyPointOffset.Add(new PointF((float)(((double)point.X - (double)pt.X) * -1.0), (float)(((double)point.Y - (double)pt.Y) * -1.0)));
                                mapView.PolygonEditDlg.SuperPolygon.Points[index] = new PointF((float)pt.X - mapView.PolyPointOffset[index].X, (float)pt.Y - mapView.PolyPointOffset[index].Y);
                            }
                            miniViewPanel.Cursor = Cursors.SizeAll;
                            Invalidate(true);
                        }
                    }
                    else
                        MapInterface.HandleLMouseClick(pt);
                    Invalidate(rc, true);
                }
                else
                {
                    if (miniViewPanel.Cursor == Cursors.SizeAll)
                        miniViewPanel.Cursor = Cursors.Default;
                    if (mapView.PolyPointOffset.Count > 0)
                        mapView.PolyPointOffset.Clear();
                }
                if (e.Button == MouseButtons.Right)
                {
                    RightDown = true;
                    Point pt = new Point(e.X * 2 * MapView.squareSize / (mapZoom * 2), e.Y * 2 * MapView.squareSize / (mapZoom * 2));
                    rc = new Rectangle(new Point(e.X + 100 + miniViewPanel.Left, e.Y - 3 + miniViewPanel.Top), new Size(60, 60));
                    MapInterface.HandleRMouseClick(pt);
                    Invalidate(rc, true);
                }
            }
            if (!miniLineWall.Checked || !mouseKeep.IsEmpty || MapInterface.CurrentMode != EditMode.WALL_BRUSH)
                return;
            MapInterface.ResetUpdateTracker();
        }
        private void miniViewPanel_Resize(object sender, EventArgs e)
        {
            if (panelTabs.SelectedIndex == 1)
            {
                if (!mapView.PolygonEditDlg.Visible) return;

                Point po = new Point(miniViewPanel.Width, 0);
                po = miniViewPanel.PointToScreen(po);
                if (Location.X + Width < po.X + mapView.PolygonEditDlg.Width) return;
                if (!IsOnScreen(new Point(po.X + mapView.PolygonEditDlg.Width, po.Y))) return;
                mapView.PolygonEditDlg.Location = po;
            }
            else
            {
                if (panelTabs.SelectedIndex != 0 || !minimap.Visible)
                    return;
                minimap.setPos();
            }
        }

        private void miniEdit_CheckedChanged(object sender, EventArgs e)
        {
            if (miniEdit.Checked)
                MiniEditPanel.Enabled = true;
            else
                MiniEditPanel.Enabled = false;
        }
        private void miniWallBrush_CheckedChanged(object sender, EventArgs e)
        {
            if (miniWallBrush.Checked)
            {
                MapInterface.CurrentMode = EditMode.WALL_BRUSH;
                miniLineWall.Visible = true;
            }
            else
                miniLineWall.Visible = false;

            Reload();
        }
        private void miniTileBrush_CheckedChanged(object sender, EventArgs e)
        {
            if (miniTileBrush.Checked)
                MapInterface.CurrentMode = EditMode.FLOOR_BRUSH;

            Reload();
        }
        private void miniTilePLace_CheckedChanged(object sender, EventArgs e)
        {
            if (miniTilePLace.Checked)
                MapInterface.CurrentMode = EditMode.FLOOR_PLACE;

            Reload();
        }
        private void miniLineWall_CheckedChanged(object sender, EventArgs e)
        {
            mapView.WallMakeNewCtrl.LineWall.Checked = miniLineWall.Checked;
            mapView.WallMakeNewCtrl.RecWall.Checked = mapView.WallMakeNewCtrl.LineWall.Checked ? false : mapView.WallMakeNewCtrl.RecWall.Checked;

        }
        private void miniUndo_Click(object sender, EventArgs e)
        {
            if (mapView.StopUndo || mapView.BlockTime) return;
            mapView.Undo(false);
            lastMapImage = null;
            mapView.MapRenderer.UpdateCanvas(false, true);
            Invalidate(true);
            RestrictWallTilesOnly();
        }
        private void miniRedo_Click(object sender, EventArgs e)
        {
            if (mapView.StopRedo || mapView.BlockTime) return;
            mapView.Redo(false);
            lastMapImage = null;
            mapView.MapRenderer.UpdateCanvas(false, true);
            Invalidate(true);
            RestrictWallTilesOnly();
        }
        private void miniUndo_EnabledChanged(object sender, EventArgs e)
        {
            if (miniUndo.Enabled)
                miniUndo.BackgroundImage = Properties.Resources.undo;
            else
                miniUndo.BackgroundImage = Properties.Resources.undoDisabled;
        }
        private void miniRedo_EnabledChanged(object sender, EventArgs e)
        {
            if (miniRedo.Enabled)
                miniRedo.BackgroundImage = Properties.Resources.redo;
            else
                miniRedo.BackgroundImage = Properties.Resources.redoDisabled;
        }
        private void cmdPolygons_Click(object sender, EventArgs e)
        {
            menuPolygons.PerformClick();
        }

        private void cmdGoToCenter_Click(object sender, EventArgs e)
        {
            mapView.CenterAtPoint(new Point((mapDimension / 2) * MapView.squareSize, (mapDimension / 2) * MapView.squareSize));
            panelTabs.SelectTab("largeMap");
            minimap.applySettings();
            minimap.setPos();
            minimap.Reload();
        }
        private void chkDivide_CheckedChanged(object sender, EventArgs e)
        {
            miniViewPanel.Refresh();
        }
        private void chkDivide2_CheckedChanged(object sender, EventArgs e)
        {
            miniViewPanel.Refresh();
        }
        #endregion
        #region Map Info Tab
        private void panelAmbientColor_Click(object sender, EventArgs e)
        {
            ColorDialog color = new ColorDialog();
            color.Color = panelAmbientColor.BackColor;
            if (color.ShowDialog(this) == DialogResult.OK)
            {
                panelAmbientColor.BackColor = color.Color;
                map.Ambient.AmbientColor = color.Color;
            }
        }
        private void chkServerPlayerLimit_CheckedChanged(object sender, EventArgs e)
        {
            mapMaxRec.Enabled = !chkServerPlayerLimit.Checked;
            mapMinRec.Enabled = !chkServerPlayerLimit.Checked;
        }
        private void chkAutoIncrement_CheckedChanged(object sender, EventArgs e)
        {
            EditorSettings.Default.Save_AutoIncrement = chkAutoIncrement.Checked;
            EditorSettings.Default.Save();
            if (chkAutoIncrement.Checked)
            {
                if (mapVersion.Text.Trim() == "")
                    mapVersion.Text = "1.0";

                mapVersion.Enabled = false;
            }
            else
                mapVersion.Enabled = true;
        }
        #endregion
        #region Map Image Tab
        private Bitmap mapImage;
        public bool imgMode = false;
        public MapImageObjectFilter mapImageFilter;

        private void cmdImgRender_Click(object sender, EventArgs e)
        {
            Cursor = Cursors.WaitCursor;
            progBarImage.Value = 25;
            if (mapImage != null)
                mapImage.Dispose();
            if (picMapImage.Image != null)
                picMapImage.Image.Dispose();

            SetImageRenderMode(chkImgUseCurrentSettings.Checked);

            mapImage = mapView.MapToImage();
            progBarImage.Value = 50;
            if (mapImage != null)
            {
                int size = (int)(5880.0 * (trackImgSize.Value / 100.0));
                if (chkImgAutoCrop.Checked)
                    mapImage = ImageHelper.SmartCrop(mapImage, size, (int)numImgPadding.Value);
                else
                    mapImage = ImageHelper.ResizeImage(mapImage, new Size(size, size), true);

                progBarImage.Value = 75;
                if (mapImage != null)
                {
                    var fitImage = ImageHelper.ResizeImage(mapImage, picMapImage.Size, true);
                    picMapImage.Image = fitImage;
                    cmdImgExport.Enabled = true;
                }
                progBarImage.Value = 100;
            }
            GC.Collect();
            Cursor = Cursors.Default;
            mapView.MapRenderer.ColorLayout.Background = Color.Black;
            progBarImage.Value = 0;
            EditorSettings.Default.Reload();
        }
        private void RenderImageAndExit(string outFile, int size, bool full)
        {
            int code = 0;
            try
            {
                SetImageRenderMode(false);
                Bitmap whole = mapView.MapToImage();
                Bitmap image = full ? ImageHelper.ResizeImage(whole, new Size(size, size), true) : ImageHelper.SmartCrop(whole, size, 20);
                if (full) whole.Dispose();
                image.Save(outFile, System.Drawing.Imaging.ImageFormat.Png);
                image.Dispose();
            }
            catch (Exception ex)
            {
                File.WriteAllText(outFile + ".error.txt", ex.ToString());
                code = 1;
            }
            EditorSettings.Default.Reload();
            Environment.Exit(code);
        }
        private void cmdImgExport_Click(object sender, EventArgs e)
        {
            if (mapImage != null)
            {
                SaveFileDialog sfd = new SaveFileDialog();
                sfd.Filter = "JPEG Image|*.jpg|PNG Image|*.png|Windows Bitmap|*.bmp";
                sfd.AddExtension = true;
                sfd.ValidateNames = true;
                sfd.OverwritePrompt = true;
                if (map.FileName != "")
                {
                    sfd.FileName = Path.GetFileNameWithoutExtension(map.FileName);
                    sfd.InitialDirectory = Path.GetDirectoryName(map.FileName);
                }
                var dr = sfd.ShowDialog();
                if (dr != DialogResult.Cancel)
                {
                    System.Drawing.Imaging.ImageFormat imageFormat;
                    switch (sfd.FilterIndex)
                    {
                        case 1:
                            imageFormat = System.Drawing.Imaging.ImageFormat.Jpeg;
                            break;
                        case 2:
                            imageFormat = System.Drawing.Imaging.ImageFormat.Png;
                            break;
                        case 3:
                            imageFormat = System.Drawing.Imaging.ImageFormat.Bmp;
                            break;
                        default:
                            return;
                    }
                    mapImage.Save(sfd.FileName, imageFormat);
                    try { Process.Start("explorer.exe", sfd.FileName); }
                    catch { }
                }
            }
            else
                cmdImgExport.Enabled = false;
        }

        private void SetImageRenderMode(bool useCurrentSettings)
        {
            if (useCurrentSettings)
            {
                EditorSettings.Default.Reload();
                imgMode = false;
            }
            else
            {
                imgMode = true;
                EditorSettings.Default.Draw_AllExtents = false;
                EditorSettings.Default.Draw_AllText = false;
                EditorSettings.Default.Draw_ComplexPreview = true;
                EditorSettings.Default.Draw_Extents = false;
                EditorSettings.Default.Draw_Extents_3D = false;
                EditorSettings.Default.Draw_FloorTiles = true;
                EditorSettings.Default.Draw_Grid = false;
                EditorSettings.Default.Draw_ObjCustomLabels = false;
                EditorSettings.Default.Draw_ObjectFacing = false;
                EditorSettings.Default.Draw_Objects = true;
                EditorSettings.Default.Draw_ObjTeams = false;
                EditorSettings.Default.Draw_ObjThingNames = false;
                EditorSettings.Default.Draw_Polygons = false;
                EditorSettings.Default.Draw_PreviewTexEdges = true;
                EditorSettings.Default.Draw_Teleports = false;
                EditorSettings.Default.Draw_Walls = true;
                EditorSettings.Default.Draw_Waypoints = false;
                EditorSettings.Default.Edit_PreviewMode = true;

                mapImageFilter = new MapImageObjectFilter();
                mapImageFilter.Armor = chkImgArmor.Checked;
                mapImageFilter.Weapons = chkImgWeapons.Checked;
                mapImageFilter.Potions = chkImgPotions.Checked;
                mapImageFilter.Food = chkImgFood.Checked;
                mapImageFilter.Crystals = chkImgCrystals.Checked;
                mapImageFilter.Gold = chkImgGold.Checked;
                mapImageFilter.Chests = chkImgChests.Checked;
                mapImageFilter.Easy = chkImgEasy.Checked;
                mapImageFilter.Hard = chkImgHard.Checked;
                mapImageFilter.Boss = chkImgBoss.Checked;
                mapImageFilter.Ambient = chkImgAmbient.Checked;
                mapImageFilter.Broken = chkImgBroken.Checked;

                mapView.MapRenderer.ColorLayout.Background = (chkImgBackground.Checked) ? Color.Black : Color.Transparent;
            }
        }
        private void chkImgAutoCrop_CheckedChanged(object sender, EventArgs e)
        {
            if (!chkImgAutoCrop.Checked)
            {
                numImgPadding.Value = 0;
                numImgPadding.Enabled = false;
            }
            else
            {
                numImgPadding.Enabled = true;
                numImgPadding.Value = 10;
            }
        }
        private void chkImgUseCurrentSettings_CheckedChanged(object sender, EventArgs e)
        {
            groupImgObjects.Enabled = !chkImgUseCurrentSettings.Checked;
            groupImgEntities.Enabled = !chkImgUseCurrentSettings.Checked;

            chkImgAutoCrop.Checked = !chkImgUseCurrentSettings.Checked;
            chkImgAutoCrop.Enabled = !chkImgUseCurrentSettings.Checked;
        }
        private void trackImgSize_Scroll(object sender, EventArgs e)
        {
            int size = (int)(5880.0 * (trackImgSize.Value / 100.0));
            lblImgDimensions.Text = size + " x " + size + "  (" + trackImgSize.Value + "%)";
        }
        #endregion

        /* ####  FUNCTIONS  #### */
        private void SaveMap()
        {
            bool playerStart = false;

            Cursor = Cursors.WaitCursor;

            // MaximumLength is set in Map Info tab respectively although either way, will not crash on Save/Load
            map.Info.Type = (Map.MapInfo.MapType)Map.MapInfo.MapTypeNames.GetKey(mapType.SelectedIndex);
            map.Info.Summary = mapSummary.Text;
            map.Info.Description = mapDescription.Text;

            map.Info.Author = mapAuthor.Text;
            map.Info.Email = mapEmail.Text;
            map.Info.Author2 = mapAuthor2.Text;
            map.Info.Email2 = mapEmail2.Text;

            if (chkAutoIncrement.Checked)
            {
                if (mapVersion.Text.Trim() == "")
                    mapVersion.Text = "1.0";

                double v;
                try
                {
                    v = double.Parse(mapVersion.Text);
                    v += 0.01;
                    mapVersion.Text = v.ToString();
                }
                catch { }
            }
            map.Info.Version = mapVersion.Text;
            map.Info.Copyright = mapCopyright.Text;
            map.Info.Date = mapDate.Text;

            if (chkServerPlayerLimit.Checked)
            {
                map.Info.RecommendedMax = 16;
                map.Info.RecommendedMin = 2;
            }
            else
            {
                try
                {
                    map.Info.RecommendedMin = mapMinRec.Text.Length == 0 ? (byte)0 : Convert.ToByte(mapMinRec.Text);
                    map.Info.RecommendedMax = mapMaxRec.Text.Length == 0 ? (byte)0 : Convert.ToByte(mapMaxRec.Text);
                }
                catch
                {
                    MessageBox.Show("Failed to parse min/max players, please revise.");
                    panelTabs.SelectTab(2);
                    minimap.Hide();
                    Cursor = Cursors.Default;
                    return;
                }
            }
            map.Info.QIntroTitle = questTitle.Text;
            map.Info.QIntroGraphic = questGraphic.Text;

            foreach (Map.Object obj in map.Objects)
            {
                if (obj.Name == "PlayerStart")
                    playerStart = true;
            }

            if (!playerStart)
            {
                MessageBox.Show("Warning: There is no PlayerStart object in this map. Every multiplayer map needs at least one this object to work properly.", "Missing PlayerStart", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                panelTabs.SelectTab(0);
                panelTabs_MouseClick(null, null);
                mapView.PlayerStartSelect();
                Cursor = Cursors.Default;
                return;
            }
            map.WriteMap();

            if (EditorSettings.Default.Save_ExportNXZ)
            {
                try
                {
                    map.WriteNxz();
                }
                catch (Exception ex)
                {
                    Logger.Log("Failed to write .nxz file! \n" + ex.Message);
                    MessageBox.Show("Couldn't write the compressed map. Try changing your map in any way and saving again.");
                }
            }

            Cursor = Cursors.Default;
            SetWindowText();

            mapView.MapRenderer.UpdateCanvas(true, false);
            mapView.mapPanel.Invalidate();
        }
        private void LoadNewMap()
        {
            MapInterface.SwitchMap(null);
            UpdateMapInfo();
        }
        public void Reload()
        {
            minimap.Reload();
            lastMapImage = null;
            Invalidate(true);
        }
        public void UpdateMapInfo()
        {
            mapView.SelectedObjects.Items.Clear();

            mapType.SelectedIndex = Map.MapInfo.MapTypeNames.IndexOfKey(map.Info.Type);
            mapSummary.Text = map.Info.Summary;
            mapDescription.Text = map.Info.Description;

            mapAuthor.Text = map.Info.Author;
            mapEmail.Text = map.Info.Email;
            mapAuthor2.Text = map.Info.Author2;
            mapEmail2.Text = map.Info.Email2;

            mapVersion.Text = map.Info.Version;
            mapCopyright.Text = map.Info.Copyright;
            mapDate.Text = map.Info.Date;

            mapMinRec.Text = string.Format("{0}", map.Info.RecommendedMin);
            mapMaxRec.Text = string.Format("{0}", map.Info.RecommendedMax);
            chkServerPlayerLimit.Checked = false;
            // если ст??дв?ну? значит нужн?использовать настройк?сервер?
            // игра пр?загрузке ставит 2 - 16
            if (map.Info.RecommendedMin == 0 && map.Info.RecommendedMax == 0)
                chkServerPlayerLimit.Checked = true;

            questTitle.Text = map.Info.QIntroTitle;
            questGraphic.Text = map.Info.QIntroGraphic;

            panelAmbientColor.BackColor = map.Ambient.AmbientColor;
            // ме?ем заголово?окна
            SetWindowText();

            mapView.MapRenderer.UpdateCanvas(true, true);
            Invalidate(true);
        }
        private void SetWindowText()
        {
            Text = string.Format(TITLE_FORMAT, map.FileName, map.Info.Summary, AboutDialog.GetVersion(), (map.Info.Version.Trim() != "" ? " " + map.Info.Version : ""));
        }
        public void SetGroups(Map.GroupData groupData)
        {
            map.Groups = groupData;
        }
        private void CreateScriptDependancies()
        {
            // Ensure compiler/decompiler are present
            try
            {
                var compilerPath = Path.Combine(Application.StartupPath, "noxscript");
                if (!Directory.Exists(compilerPath))
                    Directory.CreateDirectory(compilerPath);

                var comp1 = compilerPath + "\\nsc.exe";
                var comp2 = compilerPath + "\\nsdc.exe";
                if (!File.Exists(comp1))
                    File.WriteAllBytes(comp1, Properties.Resources.nsc);
                if (!File.Exists(comp2))
                    File.WriteAllBytes(comp2, Properties.Resources.nsdc);
            }
            catch (Exception ex) { Logger.Log("Failed to write compiler executables to noxscripts: " + ex.Message); }

            // Ensure function descriptions are present
            try
            {
                var funcDescPath = Path.Combine(Application.StartupPath, "functiondescs");
                if (!Directory.Exists(funcDescPath))
                    Directory.CreateDirectory(funcDescPath);

                // Loop through resources and only create RTFs
                System.Resources.ResourceSet resourceSet = Properties.Resources.ResourceManager.GetResourceSet(CultureInfo.CurrentUICulture, true, true);
                foreach (DictionaryEntry entry in resourceSet)
                {
                    var resName = entry.Key.ToString().Replace("_", "");
                    var byteString = entry.Value.ToString();
                    if (byteString.StartsWith("{\\rtf1"))
                    {
                        var path = Path.Combine(funcDescPath, resName + ".rtf");
                        if (!File.Exists(path))
                            File.WriteAllText(path, byteString);
                    }
                }
            }
            catch (Exception ex) { Logger.Log("Failed to write richtext files to functiondescs: " + ex.Message); }
        }
        private void LoadRecentItems()
        {
            EditorSettings.Default.Reload();
            var recentFiles = EditorSettings.Default.RecentFiles;
            if (recentFiles.Count > 1)
                recentFiles.Remove("Empty");

            menuRecent.DropDownItems.Clear();
            foreach (var file in recentFiles)
                menuRecent.DropDownItems.Add(file);
        }
        public void StoreRecentItem(string filename)
        {
            if ((filename == null) || (filename.Trim() == ""))
                return;

            if (!EditorSettings.Default.RecentFiles.Contains(filename))
            {
                // Remove old entries
                while (EditorSettings.Default.RecentFiles.Count > 20)
                    EditorSettings.Default.RecentFiles.RemoveAt(EditorSettings.Default.RecentFiles.Count - 1);

                EditorSettings.Default.RecentFiles.Insert(0, filename);
                EditorSettings.Default.Save();
            }
            else
            {
                // Bump to top
                EditorSettings.Default.RecentFiles.Remove(filename);
                EditorSettings.Default.RecentFiles.Insert(0, filename);
            }
            EditorSettings.Default.Save();
            LoadRecentItems();
        }

        private string GetBaseMode(EditMode mode)
        {
            string modeString = mode.ToString();

            modeString = modeString.Substring(0, modeString.IndexOf("_")).Trim();

            return modeString;
        }
        private void RestrictWallTilesOnly()
        {
            int steps = (mapView.TimeManager.Count - 1) - mapView.currentStep;
            if (steps > 0)
            {
                if (GetBaseMode(mapView.TimeManager[steps - 1].Mode) != "WALL" && GetBaseMode(mapView.TimeManager[steps - 1].Mode) != "FLOOR" && GetBaseMode(mapView.TimeManager[steps - 1].Mode) != "POLYGON")
                    miniUndo.Enabled = false;
            }

            if (mapView.currentStep > 0)
            {
                if (GetBaseMode(mapView.TimeManager[steps + 1].Mode) != "WALL" && GetBaseMode(mapView.TimeManager[steps + 1].Mode) != "FLOOR" && GetBaseMode(mapView.TimeManager[steps + 1].Mode) != "POLYGON")
                    miniRedo.Enabled = false;
            }
        }
        private bool IsOnScreen(Point pt)
        {
            Screen[] screens = Screen.AllScreens;
            foreach (Screen screen in screens)
            {
                if (screen.WorkingArea.Contains(pt))
                    return true;
            }
            return false;
        }

        private bool GrantAccess(string fullPath)
        {
            DirectoryInfo dInfo = new DirectoryInfo(fullPath);
            System.Security.AccessControl.DirectorySecurity dSecurity = dInfo.GetAccessControl();
            dSecurity.AddAccessRule(new System.Security.AccessControl.FileSystemAccessRule(new System.Security.Principal.SecurityIdentifier(System.Security.Principal.WellKnownSidType.WorldSid, null), System.Security.AccessControl.FileSystemRights.FullControl, System.Security.AccessControl.InheritanceFlags.ObjectInherit | System.Security.AccessControl.InheritanceFlags.ContainerInherit, System.Security.AccessControl.PropagationFlags.NoPropagateInherit, System.Security.AccessControl.AccessControlType.Allow));
            dInfo.SetAccessControl(dSecurity);
            return true;
        }
        public bool ProcessCmdKeyFromChildForm(ref Message msg, Keys keyData)
        {
            Message msg1 = msg;
            msg1.HWnd = Handle;
            return ProcessCmdKey(ref msg1, keyData);
        }
        public static IList GetSupportedCultures()
        {
            // Not really sure why this function is here
            ArrayList list = new ArrayList();
            list.Add(CultureInfo.InvariantCulture);
            foreach (CultureInfo culture in CultureInfo.GetCultures(CultureTypes.AllCultures))
            {
                try
                {
                    Assembly.GetExecutingAssembly().GetSatelliteAssembly(culture);
                    list.Add(culture); // won't get added if not found (exception will be thrown)
                }
                catch (Exception) { }
            }
            return list;
        }

        #region Windows Form Designer generated code
        private System.ComponentModel.IContainer components;
        private TabPage largeMap;
        public TabControl panelTabs;
        private TabPage mapInfoTab;
        private Label labelTitle;
        private GroupBox groupMapInfoTab;
        private TextBox mapSummary;
        private Label labelDescription;
        private Label labelVersion;
        private TextBox mapDescription;
        private Label labelAuthor;
        private Label labelAuthor2;
        private Label labelEmail;
        private Label labelEmail2;
        private TextBox mapAuthor;
        private TextBox mapEmail;
        private TextBox mapEmail2;
        private TextBox mapAuthor2;
        private Label labelDate;
        private TextBox mapDate;
        private TextBox mapVersion;
        private Label labelCopyright;
        private Label minRecLbl;
        private Label maxRecLbl;
        private Label recommendedLbl;
        private Label mapTypeLbl;
        private TextBox mapMinRec;
        private TextBox mapMaxRec;
        private ComboBox mapType;
        private TextBox mapCopyright;
        private Label label1;
        private Label label2;
        private TextBox questTitle;
        private TextBox questGraphic;
        private Label label3;
        private TabPage minimapTab;
        private Panel MinimapPanel;
        private GroupBox groupMiniMapTab;
        private Button cmdGoToCenter;
        private CheckBox chkDivide;
        private CheckBox chkDivide2;
        private Label label4;
        private Panel panelAmbientColor;
        private Panel panelInnerMinimap;
        private NumericUpDown numMinimapZoom;
        private Label label5;
        private CheckBox miniEdit;
        private Panel MiniEditPanel;
        private Label labelSep2;
        private RadioButton miniTileBrush;
        private RadioButton miniTilePLace;
        private RadioButton miniWallBrush;
        private NumericUpDown numBrushSize;
        private Label label8;
        private Label label7;
        private Label label6;
        public CheckBox miniLineWall;
        public Button miniRedo;
        public Button miniUndo;
        private Label label9;
        private Button cmdPolygons;
        private Label label10;
        private CheckBox chkServerPlayerLimit;
        private CheckBox chkAutoIncrement;
        private Button cmdDebug;

        private MenuStrip mainMenuStrip;
        private ToolStripMenuItem menuFile;
        private ToolStripMenuItem menuNew;
        private ToolStripMenuItem menuOpen;
        private ToolStripMenuItem menuInstallMap;
        private ToolStripMenuItem menuRecent;
        public ToolStripMenuItem menuSave;
        private ToolStripMenuItem menuSaveAs;
        private ToolStripSeparator toolStripSeparator1;
        private ToolStripMenuItem menuImportSave;
        private ToolStripMenuItem menuImportScript;
        private ToolStripMenuItem menuExportScript;
        private ToolStripMenuItem menuExportNativeScript;
        private ToolStripSeparator toolStripSeparator2;
        private ToolStripMenuItem menuExit;
        private ToolStripMenuItem menuMap;
        private ToolStripMenuItem menuOptions;
        private ToolStripMenuItem menuHelp;
        private ToolStripMenuItem menuShortcuts;
        private ToolStripMenuItem menuUndo;
        private ToolStripMenuItem menuRedo;
        private ToolStripMenuItem menuListObjects;
        private ToolStripMenuItem menuScripts;
        private ToolStripMenuItem menuGroups;
        private ToolStripMenuItem menuPolygons;
        private ToolStripSeparator toolStripSeparator3;
        private ToolStripMenuItem menuFixExtents;
        private ToolStripMenuItem menuMapGenerator;
        private ToolStripMenuItem menuShowGrid;
        private ToolStripMenuItem menuShowMinimap;
        public ToolStripMenuItem menuVisualPreviewMode;
        private ToolStripMenuItem menuInvertColors;
        private ToolStripSeparator toolStripSeparator4;
        public ToolStripMenuItem menuSettings;
        private ToolStripMenuItem menuHelpLink1;
        private ToolStripMenuItem menuHelpLink2;
        private ToolStripSeparator toolStripSeparator5;
        private ToolStripMenuItem menuHelpLink3;
        private ToolStripMenuItem menuHelpLink4;
        private ToolStripSeparator toolStripSeparator6;
        private ToolStripMenuItem menuAbout;
        private ToolStripMenuItem menuPicker;
        private ToolStripMenuItem menuRectangleDraw;
        private ToolStripMenuItem menuLineDraw;
        private ToolStripMenuItem menuRotateSelection45;
        private ToolStripMenuItem menuDrawWalls;
        private ToolStripMenuItem menuDrawObjects;
        private ToolStripMenuItem menuDraw3DExtents;
        private ToolStripMenuItem menuDrawWaypoints;
        private ToolStripMenuItem menuDrawTeleportPaths;
        private ToolStripMenuItem menuColorSpecialWalls;

        private TabPage mapImageTab;
        private PictureBox picMapImage;
        private GroupBox groupImgExport;
        private Label lblImgDimensions;
        private TrackBar trackImgSize;
        private Label lblImgSize;
        private NumericUpDown numImgPadding;
        private Label lblImgPadding;
        private CheckBox chkImgAutoCrop;
        private GroupBox groupImgEntities;
        private CheckBox chkImgBroken;
        private CheckBox chkImgBoss;
        private CheckBox chkImgAmbient;
        private CheckBox chkImgHard;
        private CheckBox chkImgEasy;
        private ProgressBar progBarImage;
        private GroupBox groupImgObjects;
        private CheckBox chkImgQuest;
        private CheckBox chkImgChests;
        private CheckBox chkImgFood;
        private CheckBox chkImgWeapons;
        private CheckBox chkImgCrystals;
        private CheckBox chkImgGold;
        private CheckBox chkImgPotions;
        private CheckBox chkImgArmor;
        private CheckBox chkImgUseCurrentSettings;
        private Button cmdImgExport;
        private CheckBox chkImgBackground;
        private Button cmdImgRender;

        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(MainWindow));
            this.mapInfoTab = new System.Windows.Forms.TabPage();
            this.groupMapInfoTab = new System.Windows.Forms.GroupBox();
            this.chkServerPlayerLimit = new System.Windows.Forms.CheckBox();
            this.label4 = new System.Windows.Forms.Label();
            this.panelAmbientColor = new System.Windows.Forms.Panel();
            this.label3 = new System.Windows.Forms.Label();
            this.questGraphic = new System.Windows.Forms.TextBox();
            this.questTitle = new System.Windows.Forms.TextBox();
            this.label2 = new System.Windows.Forms.Label();
            this.label1 = new System.Windows.Forms.Label();
            this.mapType = new System.Windows.Forms.ComboBox();
            this.mapTypeLbl = new System.Windows.Forms.Label();
            this.recommendedLbl = new System.Windows.Forms.Label();
            this.maxRecLbl = new System.Windows.Forms.Label();
            this.minRecLbl = new System.Windows.Forms.Label();
            this.mapMaxRec = new System.Windows.Forms.TextBox();
            this.mapMinRec = new System.Windows.Forms.TextBox();
            this.mapCopyright = new System.Windows.Forms.TextBox();
            this.labelCopyright = new System.Windows.Forms.Label();
            this.mapVersion = new System.Windows.Forms.TextBox();
            this.mapDate = new System.Windows.Forms.TextBox();
            this.labelDate = new System.Windows.Forms.Label();
            this.mapAuthor2 = new System.Windows.Forms.TextBox();
            this.mapEmail2 = new System.Windows.Forms.TextBox();
            this.mapEmail = new System.Windows.Forms.TextBox();
            this.mapAuthor = new System.Windows.Forms.TextBox();
            this.labelEmail2 = new System.Windows.Forms.Label();
            this.labelEmail = new System.Windows.Forms.Label();
            this.labelAuthor2 = new System.Windows.Forms.Label();
            this.labelAuthor = new System.Windows.Forms.Label();
            this.labelVersion = new System.Windows.Forms.Label();
            this.mapDescription = new System.Windows.Forms.TextBox();
            this.labelDescription = new System.Windows.Forms.Label();
            this.labelTitle = new System.Windows.Forms.Label();
            this.mapSummary = new System.Windows.Forms.TextBox();
            this.chkAutoIncrement = new System.Windows.Forms.CheckBox();
            this.minimapTab = new System.Windows.Forms.TabPage();
            this.MinimapPanel = new System.Windows.Forms.Panel();
            this.panelInnerMinimap = new System.Windows.Forms.Panel();
            this.miniViewPanel = new MapEditor.MainWindow.FlickerFreePanel();
            this.groupMiniMapTab = new System.Windows.Forms.GroupBox();
            this.cmdDebug = new System.Windows.Forms.Button();
            this.MiniEditPanel = new System.Windows.Forms.Panel();
            this.label10 = new System.Windows.Forms.Label();
            this.cmdPolygons = new System.Windows.Forms.Button();
            this.label9 = new System.Windows.Forms.Label();
            this.miniRedo = new System.Windows.Forms.Button();
            this.miniUndo = new System.Windows.Forms.Button();
            this.miniLineWall = new System.Windows.Forms.CheckBox();
            this.label8 = new System.Windows.Forms.Label();
            this.label7 = new System.Windows.Forms.Label();
            this.label6 = new System.Windows.Forms.Label();
            this.numBrushSize = new System.Windows.Forms.NumericUpDown();
            this.miniTileBrush = new System.Windows.Forms.RadioButton();
            this.miniTilePLace = new System.Windows.Forms.RadioButton();
            this.miniWallBrush = new System.Windows.Forms.RadioButton();
            this.labelSep2 = new System.Windows.Forms.Label();
            this.miniEdit = new System.Windows.Forms.CheckBox();
            this.label5 = new System.Windows.Forms.Label();
            this.numMinimapZoom = new System.Windows.Forms.NumericUpDown();
            this.chkDivide2 = new System.Windows.Forms.CheckBox();
            this.chkDivide = new System.Windows.Forms.CheckBox();
            this.cmdGoToCenter = new System.Windows.Forms.Button();
            this.largeMap = new System.Windows.Forms.TabPage();
            this.suggestBox = new System.Windows.Forms.ListBox();
            this.mapView = new MapEditor.MapView();
            this.panelTabs = new System.Windows.Forms.TabControl();
            this.mapImageTab = new System.Windows.Forms.TabPage();
            this.cmdImgRender = new System.Windows.Forms.Button();
            this.groupImgExport = new System.Windows.Forms.GroupBox();
            this.chkImgBackground = new System.Windows.Forms.CheckBox();
            this.lblImgDimensions = new System.Windows.Forms.Label();
            this.trackImgSize = new System.Windows.Forms.TrackBar();
            this.numImgPadding = new System.Windows.Forms.NumericUpDown();
            this.lblImgPadding = new System.Windows.Forms.Label();
            this.chkImgAutoCrop = new System.Windows.Forms.CheckBox();
            this.lblImgSize = new System.Windows.Forms.Label();
            this.cmdImgExport = new System.Windows.Forms.Button();
            this.groupImgEntities = new System.Windows.Forms.GroupBox();
            this.chkImgBroken = new System.Windows.Forms.CheckBox();
            this.chkImgBoss = new System.Windows.Forms.CheckBox();
            this.chkImgAmbient = new System.Windows.Forms.CheckBox();
            this.chkImgHard = new System.Windows.Forms.CheckBox();
            this.chkImgEasy = new System.Windows.Forms.CheckBox();
            this.progBarImage = new System.Windows.Forms.ProgressBar();
            this.groupImgObjects = new System.Windows.Forms.GroupBox();
            this.chkImgQuest = new System.Windows.Forms.CheckBox();
            this.chkImgChests = new System.Windows.Forms.CheckBox();
            this.chkImgFood = new System.Windows.Forms.CheckBox();
            this.chkImgWeapons = new System.Windows.Forms.CheckBox();
            this.chkImgCrystals = new System.Windows.Forms.CheckBox();
            this.chkImgGold = new System.Windows.Forms.CheckBox();
            this.chkImgPotions = new System.Windows.Forms.CheckBox();
            this.chkImgArmor = new System.Windows.Forms.CheckBox();
            this.chkImgUseCurrentSettings = new System.Windows.Forms.CheckBox();
            this.picMapImage = new System.Windows.Forms.PictureBox();
            this.mainMenuStrip = new System.Windows.Forms.MenuStrip();
            this.menuFile = new System.Windows.Forms.ToolStripMenuItem();
            this.menuNew = new System.Windows.Forms.ToolStripMenuItem();
            this.menuOpen = new System.Windows.Forms.ToolStripMenuItem();
            this.menuRecent = new System.Windows.Forms.ToolStripMenuItem();
            this.menuInstallMap = new System.Windows.Forms.ToolStripMenuItem();
            this.menuSave = new System.Windows.Forms.ToolStripMenuItem();
            this.menuSaveAs = new System.Windows.Forms.ToolStripMenuItem();
            this.menuSaveNXZOnly = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator1 = new System.Windows.Forms.ToolStripSeparator();
            this.menuImportSave = new System.Windows.Forms.ToolStripMenuItem();
            this.menuImportScript = new System.Windows.Forms.ToolStripMenuItem();
            this.menuExportScript = new System.Windows.Forms.ToolStripMenuItem();
            this.menuExportNativeScript = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator2 = new System.Windows.Forms.ToolStripSeparator();
            this.menuExit = new System.Windows.Forms.ToolStripMenuItem();
            this.menuMap = new System.Windows.Forms.ToolStripMenuItem();
            this.menuListObjects = new System.Windows.Forms.ToolStripMenuItem();
            this.menuScripts = new System.Windows.Forms.ToolStripMenuItem();
            this.menuGroups = new System.Windows.Forms.ToolStripMenuItem();
            this.menuPolygons = new System.Windows.Forms.ToolStripMenuItem();
            this.menuWaypoints = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator3 = new System.Windows.Forms.ToolStripSeparator();
            this.menuFixExtents = new System.Windows.Forms.ToolStripMenuItem();
            this.menuMapGenerator = new System.Windows.Forms.ToolStripMenuItem();
            this.menuOptions = new System.Windows.Forms.ToolStripMenuItem();
            this.menuShowGrid = new System.Windows.Forms.ToolStripMenuItem();
            this.menuShowMinimap = new System.Windows.Forms.ToolStripMenuItem();
            this.menuVisualPreviewMode = new System.Windows.Forms.ToolStripMenuItem();
            this.menuInvertColors = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator4 = new System.Windows.Forms.ToolStripSeparator();
            this.menuSettings = new System.Windows.Forms.ToolStripMenuItem();
            this.menuHelp = new System.Windows.Forms.ToolStripMenuItem();
            this.menuHelpLink1 = new System.Windows.Forms.ToolStripMenuItem();
            this.menuHelpLink2 = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator5 = new System.Windows.Forms.ToolStripSeparator();
            this.menuHelpLink3 = new System.Windows.Forms.ToolStripMenuItem();
            this.menuHelpLink4 = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator6 = new System.Windows.Forms.ToolStripSeparator();
            this.menuAbout = new System.Windows.Forms.ToolStripMenuItem();
            this.menuShortcuts = new System.Windows.Forms.ToolStripMenuItem();
            this.menuUndo = new System.Windows.Forms.ToolStripMenuItem();
            this.menuRedo = new System.Windows.Forms.ToolStripMenuItem();
            this.menuPicker = new System.Windows.Forms.ToolStripMenuItem();
            this.menuRectangleDraw = new System.Windows.Forms.ToolStripMenuItem();
            this.menuLineDraw = new System.Windows.Forms.ToolStripMenuItem();
            this.menuRotateSelection45 = new System.Windows.Forms.ToolStripMenuItem();
            this.menuDrawWalls = new System.Windows.Forms.ToolStripMenuItem();
            this.menuDrawObjects = new System.Windows.Forms.ToolStripMenuItem();
            this.menuDraw3DExtents = new System.Windows.Forms.ToolStripMenuItem();
            this.menuDrawTeleportPaths = new System.Windows.Forms.ToolStripMenuItem();
            this.menuDrawWaypoints = new System.Windows.Forms.ToolStripMenuItem();
            this.menuColorSpecialWalls = new System.Windows.Forms.ToolStripMenuItem();
            this.menuHelpLink5 = new System.Windows.Forms.ToolStripMenuItem();
            this.mapInfoTab.SuspendLayout();
            this.groupMapInfoTab.SuspendLayout();
            this.minimapTab.SuspendLayout();
            this.MinimapPanel.SuspendLayout();
            this.panelInnerMinimap.SuspendLayout();
            this.groupMiniMapTab.SuspendLayout();
            this.MiniEditPanel.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.numBrushSize)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.numMinimapZoom)).BeginInit();
            this.largeMap.SuspendLayout();
            this.panelTabs.SuspendLayout();
            this.mapImageTab.SuspendLayout();
            this.groupImgExport.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.trackImgSize)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.numImgPadding)).BeginInit();
            this.groupImgEntities.SuspendLayout();
            this.groupImgObjects.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.picMapImage)).BeginInit();
            this.mainMenuStrip.SuspendLayout();
            this.SuspendLayout();
            // 
            // mapInfoTab
            // 
            this.mapInfoTab.Controls.Add(this.groupMapInfoTab);
            this.mapInfoTab.Location = new System.Drawing.Point(4, 22);
            this.mapInfoTab.Name = "mapInfoTab";
            this.mapInfoTab.Size = new System.Drawing.Size(1000, 691);
            this.mapInfoTab.TabIndex = 0;
            this.mapInfoTab.Text = "Map Info";
            this.mapInfoTab.UseVisualStyleBackColor = true;
            // 
            // groupMapInfoTab
            // 
            this.groupMapInfoTab.Controls.Add(this.chkServerPlayerLimit);
            this.groupMapInfoTab.Controls.Add(this.label4);
            this.groupMapInfoTab.Controls.Add(this.panelAmbientColor);
            this.groupMapInfoTab.Controls.Add(this.label3);
            this.groupMapInfoTab.Controls.Add(this.questGraphic);
            this.groupMapInfoTab.Controls.Add(this.questTitle);
            this.groupMapInfoTab.Controls.Add(this.label2);
            this.groupMapInfoTab.Controls.Add(this.label1);
            this.groupMapInfoTab.Controls.Add(this.mapType);
            this.groupMapInfoTab.Controls.Add(this.mapTypeLbl);
            this.groupMapInfoTab.Controls.Add(this.recommendedLbl);
            this.groupMapInfoTab.Controls.Add(this.maxRecLbl);
            this.groupMapInfoTab.Controls.Add(this.minRecLbl);
            this.groupMapInfoTab.Controls.Add(this.mapMaxRec);
            this.groupMapInfoTab.Controls.Add(this.mapMinRec);
            this.groupMapInfoTab.Controls.Add(this.mapCopyright);
            this.groupMapInfoTab.Controls.Add(this.labelCopyright);
            this.groupMapInfoTab.Controls.Add(this.mapVersion);
            this.groupMapInfoTab.Controls.Add(this.mapDate);
            this.groupMapInfoTab.Controls.Add(this.labelDate);
            this.groupMapInfoTab.Controls.Add(this.mapAuthor2);
            this.groupMapInfoTab.Controls.Add(this.mapEmail2);
            this.groupMapInfoTab.Controls.Add(this.mapEmail);
            this.groupMapInfoTab.Controls.Add(this.mapAuthor);
            this.groupMapInfoTab.Controls.Add(this.labelEmail2);
            this.groupMapInfoTab.Controls.Add(this.labelEmail);
            this.groupMapInfoTab.Controls.Add(this.labelAuthor2);
            this.groupMapInfoTab.Controls.Add(this.labelAuthor);
            this.groupMapInfoTab.Controls.Add(this.labelVersion);
            this.groupMapInfoTab.Controls.Add(this.mapDescription);
            this.groupMapInfoTab.Controls.Add(this.labelDescription);
            this.groupMapInfoTab.Controls.Add(this.labelTitle);
            this.groupMapInfoTab.Controls.Add(this.mapSummary);
            this.groupMapInfoTab.Controls.Add(this.chkAutoIncrement);
            this.groupMapInfoTab.Dock = System.Windows.Forms.DockStyle.Top;
            this.groupMapInfoTab.Location = new System.Drawing.Point(0, 0);
            this.groupMapInfoTab.Name = "groupMapInfoTab";
            this.groupMapInfoTab.Size = new System.Drawing.Size(1000, 560);
            this.groupMapInfoTab.TabIndex = 2;
            this.groupMapInfoTab.TabStop = false;
            // 
            // chkServerPlayerLimit
            // 
            this.chkServerPlayerLimit.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.chkServerPlayerLimit.Location = new System.Drawing.Point(288, 373);
            this.chkServerPlayerLimit.Name = "chkServerPlayerLimit";
            this.chkServerPlayerLimit.Size = new System.Drawing.Size(104, 24);
            this.chkServerPlayerLimit.TabIndex = 34;
            this.chkServerPlayerLimit.Text = "Server Settings";
            this.chkServerPlayerLimit.UseVisualStyleBackColor = true;
            this.chkServerPlayerLimit.CheckedChanged += new System.EventHandler(this.chkServerPlayerLimit_CheckedChanged);
            // 
            // label4
            // 
            this.label4.AutoSize = true;
            this.label4.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.label4.Location = new System.Drawing.Point(256, 433);
            this.label4.Name = "label4";
            this.label4.Size = new System.Drawing.Size(72, 13);
            this.label4.TabIndex = 33;
            this.label4.Text = "Ambient Color";
            // 
            // panelAmbientColor
            // 
            this.panelAmbientColor.Location = new System.Drawing.Point(259, 459);
            this.panelAmbientColor.Name = "panelAmbientColor";
            this.panelAmbientColor.Size = new System.Drawing.Size(69, 36);
            this.panelAmbientColor.TabIndex = 32;
            this.panelAmbientColor.Click += new System.EventHandler(this.panelAmbientColor_Click);
            // 
            // label3
            // 
            this.label3.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.label3.Location = new System.Drawing.Point(72, 427);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(64, 24);
            this.label3.TabIndex = 31;
            this.label3.Text = "Quest Intro";
            this.label3.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
            // 
            // questGraphic
            // 
            this.questGraphic.Location = new System.Drawing.Point(88, 491);
            this.questGraphic.MaxLength = 512;
            this.questGraphic.Name = "questGraphic";
            this.questGraphic.Size = new System.Drawing.Size(128, 20);
            this.questGraphic.TabIndex = 30;
            // 
            // questTitle
            // 
            this.questTitle.Location = new System.Drawing.Point(88, 459);
            this.questTitle.MaxLength = 512;
            this.questTitle.Name = "questTitle";
            this.questTitle.Size = new System.Drawing.Size(128, 20);
            this.questTitle.TabIndex = 29;
            // 
            // label2
            // 
            this.label2.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.label2.Location = new System.Drawing.Point(32, 486);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(48, 24);
            this.label2.TabIndex = 28;
            this.label2.Text = "Graphic";
            this.label2.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // label1
            // 
            this.label1.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.label1.Location = new System.Drawing.Point(32, 457);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(48, 24);
            this.label1.TabIndex = 27;
            this.label1.Text = "Title";
            this.label1.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // mapType
            // 
            this.mapType.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.mapType.FormattingEnabled = true;
            this.mapType.ItemHeight = 13;
            this.mapType.Location = new System.Drawing.Point(88, 24);
            this.mapType.Name = "mapType";
            this.mapType.Size = new System.Drawing.Size(88, 21);
            this.mapType.TabIndex = 26;
            // 
            // mapTypeLbl
            // 
            this.mapTypeLbl.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.mapTypeLbl.Location = new System.Drawing.Point(24, 24);
            this.mapTypeLbl.Name = "mapTypeLbl";
            this.mapTypeLbl.Size = new System.Drawing.Size(64, 24);
            this.mapTypeLbl.TabIndex = 25;
            this.mapTypeLbl.Text = "Map Type";
            this.mapTypeLbl.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // recommendedLbl
            // 
            this.recommendedLbl.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.recommendedLbl.Location = new System.Drawing.Point(256, 322);
            this.recommendedLbl.Name = "recommendedLbl";
            this.recommendedLbl.Size = new System.Drawing.Size(184, 24);
            this.recommendedLbl.TabIndex = 24;
            this.recommendedLbl.Text = "Recommended Number of Players";
            this.recommendedLbl.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
            // 
            // maxRecLbl
            // 
            this.maxRecLbl.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.maxRecLbl.Location = new System.Drawing.Point(328, 346);
            this.maxRecLbl.Name = "maxRecLbl";
            this.maxRecLbl.Size = new System.Drawing.Size(32, 24);
            this.maxRecLbl.TabIndex = 23;
            this.maxRecLbl.Text = "Max";
            this.maxRecLbl.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // minRecLbl
            // 
            this.minRecLbl.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.minRecLbl.Location = new System.Drawing.Point(256, 346);
            this.minRecLbl.Name = "minRecLbl";
            this.minRecLbl.Size = new System.Drawing.Size(32, 24);
            this.minRecLbl.TabIndex = 22;
            this.minRecLbl.Text = "Min";
            this.minRecLbl.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // mapMaxRec
            // 
            this.mapMaxRec.Location = new System.Drawing.Point(360, 346);
            this.mapMaxRec.MaxLength = 2;
            this.mapMaxRec.Name = "mapMaxRec";
            this.mapMaxRec.Size = new System.Drawing.Size(32, 20);
            this.mapMaxRec.TabIndex = 21;
            // 
            // mapMinRec
            // 
            this.mapMinRec.Location = new System.Drawing.Point(288, 346);
            this.mapMinRec.MaxLength = 2;
            this.mapMinRec.Name = "mapMinRec";
            this.mapMinRec.Size = new System.Drawing.Size(32, 20);
            this.mapMinRec.TabIndex = 20;
            // 
            // mapCopyright
            // 
            this.mapCopyright.Location = new System.Drawing.Point(88, 348);
            this.mapCopyright.MaxLength = 128;
            this.mapCopyright.Name = "mapCopyright";
            this.mapCopyright.Size = new System.Drawing.Size(128, 20);
            this.mapCopyright.TabIndex = 17;
            // 
            // labelCopyright
            // 
            this.labelCopyright.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelCopyright.Location = new System.Drawing.Point(10, 346);
            this.labelCopyright.Name = "labelCopyright";
            this.labelCopyright.Size = new System.Drawing.Size(72, 24);
            this.labelCopyright.TabIndex = 16;
            this.labelCopyright.Text = "Copyright";
            this.labelCopyright.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // mapVersion
            // 
            this.mapVersion.Location = new System.Drawing.Point(88, 373);
            this.mapVersion.MaxLength = 16;
            this.mapVersion.Name = "mapVersion";
            this.mapVersion.Size = new System.Drawing.Size(128, 20);
            this.mapVersion.TabIndex = 15;
            // 
            // mapDate
            // 
            this.mapDate.Location = new System.Drawing.Point(88, 323);
            this.mapDate.MaxLength = 32;
            this.mapDate.Name = "mapDate";
            this.mapDate.Size = new System.Drawing.Size(128, 20);
            this.mapDate.TabIndex = 14;
            // 
            // labelDate
            // 
            this.labelDate.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelDate.Location = new System.Drawing.Point(17, 322);
            this.labelDate.Name = "labelDate";
            this.labelDate.Size = new System.Drawing.Size(64, 24);
            this.labelDate.TabIndex = 13;
            this.labelDate.Text = "Date";
            this.labelDate.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // mapAuthor2
            // 
            this.mapAuthor2.Location = new System.Drawing.Point(88, 282);
            this.mapAuthor2.MaxLength = 64;
            this.mapAuthor2.Name = "mapAuthor2";
            this.mapAuthor2.Size = new System.Drawing.Size(128, 20);
            this.mapAuthor2.TabIndex = 12;
            // 
            // mapEmail2
            // 
            this.mapEmail2.Location = new System.Drawing.Point(288, 282);
            this.mapEmail2.MaxLength = 192;
            this.mapEmail2.Name = "mapEmail2";
            this.mapEmail2.Size = new System.Drawing.Size(160, 20);
            this.mapEmail2.TabIndex = 11;
            // 
            // mapEmail
            // 
            this.mapEmail.Location = new System.Drawing.Point(288, 250);
            this.mapEmail.MaxLength = 192;
            this.mapEmail.Name = "mapEmail";
            this.mapEmail.Size = new System.Drawing.Size(160, 20);
            this.mapEmail.TabIndex = 10;
            // 
            // mapAuthor
            // 
            this.mapAuthor.Location = new System.Drawing.Point(88, 250);
            this.mapAuthor.MaxLength = 64;
            this.mapAuthor.Name = "mapAuthor";
            this.mapAuthor.Size = new System.Drawing.Size(128, 20);
            this.mapAuthor.TabIndex = 9;
            // 
            // labelEmail2
            // 
            this.labelEmail2.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelEmail2.Location = new System.Drawing.Point(248, 282);
            this.labelEmail2.Name = "labelEmail2";
            this.labelEmail2.Size = new System.Drawing.Size(40, 24);
            this.labelEmail2.TabIndex = 8;
            this.labelEmail2.Text = "Email";
            this.labelEmail2.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // labelEmail
            // 
            this.labelEmail.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelEmail.Location = new System.Drawing.Point(248, 250);
            this.labelEmail.Name = "labelEmail";
            this.labelEmail.Size = new System.Drawing.Size(40, 24);
            this.labelEmail.TabIndex = 7;
            this.labelEmail.Text = "Email";
            this.labelEmail.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // labelAuthor2
            // 
            this.labelAuthor2.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelAuthor2.Location = new System.Drawing.Point(8, 282);
            this.labelAuthor2.Name = "labelAuthor2";
            this.labelAuthor2.Size = new System.Drawing.Size(72, 24);
            this.labelAuthor2.TabIndex = 6;
            this.labelAuthor2.Text = "Secondary Author";
            this.labelAuthor2.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // labelAuthor
            // 
            this.labelAuthor.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelAuthor.Location = new System.Drawing.Point(8, 250);
            this.labelAuthor.Name = "labelAuthor";
            this.labelAuthor.Size = new System.Drawing.Size(72, 24);
            this.labelAuthor.TabIndex = 5;
            this.labelAuthor.Text = "Author";
            this.labelAuthor.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // labelVersion
            // 
            this.labelVersion.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelVersion.Location = new System.Drawing.Point(9, 370);
            this.labelVersion.Name = "labelVersion";
            this.labelVersion.Size = new System.Drawing.Size(72, 24);
            this.labelVersion.TabIndex = 4;
            this.labelVersion.Text = "Version";
            this.labelVersion.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // mapDescription
            // 
            this.mapDescription.Location = new System.Drawing.Point(88, 88);
            this.mapDescription.MaxLength = 512;
            this.mapDescription.Multiline = true;
            this.mapDescription.Name = "mapDescription";
            this.mapDescription.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.mapDescription.Size = new System.Drawing.Size(360, 156);
            this.mapDescription.TabIndex = 3;
            // 
            // labelDescription
            // 
            this.labelDescription.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelDescription.Location = new System.Drawing.Point(8, 88);
            this.labelDescription.Name = "labelDescription";
            this.labelDescription.Size = new System.Drawing.Size(80, 24);
            this.labelDescription.TabIndex = 2;
            this.labelDescription.Text = "Description";
            this.labelDescription.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // labelTitle
            // 
            this.labelTitle.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.labelTitle.Location = new System.Drawing.Point(8, 56);
            this.labelTitle.Name = "labelTitle";
            this.labelTitle.Size = new System.Drawing.Size(80, 24);
            this.labelTitle.TabIndex = 0;
            this.labelTitle.Text = "Title/Summary";
            this.labelTitle.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // mapSummary
            // 
            this.mapSummary.Location = new System.Drawing.Point(88, 56);
            this.mapSummary.MaxLength = 64;
            this.mapSummary.Name = "mapSummary";
            this.mapSummary.Size = new System.Drawing.Size(360, 20);
            this.mapSummary.TabIndex = 1;
            // 
            // chkAutoIncrement
            // 
            this.chkAutoIncrement.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.chkAutoIncrement.Location = new System.Drawing.Point(88, 392);
            this.chkAutoIncrement.Name = "chkAutoIncrement";
            this.chkAutoIncrement.Size = new System.Drawing.Size(104, 24);
            this.chkAutoIncrement.TabIndex = 35;
            this.chkAutoIncrement.Text = "Auto Increment";
            this.chkAutoIncrement.UseVisualStyleBackColor = true;
            this.chkAutoIncrement.CheckedChanged += new System.EventHandler(this.chkAutoIncrement_CheckedChanged);
            // 
            // minimapTab
            // 
            this.minimapTab.Controls.Add(this.MinimapPanel);
            this.minimapTab.Location = new System.Drawing.Point(4, 22);
            this.minimapTab.Name = "minimapTab";
            this.minimapTab.Size = new System.Drawing.Size(1000, 691);
            this.minimapTab.TabIndex = 0;
            this.minimapTab.Text = "Mini Map";
            this.minimapTab.UseVisualStyleBackColor = true;
            // 
            // MinimapPanel
            // 
            this.MinimapPanel.Controls.Add(this.panelInnerMinimap);
            this.MinimapPanel.Controls.Add(this.groupMiniMapTab);
            this.MinimapPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.MinimapPanel.Location = new System.Drawing.Point(0, 0);
            this.MinimapPanel.Name = "MinimapPanel";
            this.MinimapPanel.Size = new System.Drawing.Size(1000, 691);
            this.MinimapPanel.TabIndex = 0;
            // 
            // panelInnerMinimap
            // 
            this.panelInnerMinimap.AutoScroll = true;
            this.panelInnerMinimap.Controls.Add(this.miniViewPanel);
            this.panelInnerMinimap.Dock = System.Windows.Forms.DockStyle.Fill;
            this.panelInnerMinimap.Location = new System.Drawing.Point(120, 0);
            this.panelInnerMinimap.Name = "panelInnerMinimap";
            this.panelInnerMinimap.Size = new System.Drawing.Size(880, 691);
            this.panelInnerMinimap.TabIndex = 3;
            this.panelInnerMinimap.Scroll += new System.Windows.Forms.ScrollEventHandler(this.panelInnerMinimap_Scroll);
            this.panelInnerMinimap.MouseUp += new System.Windows.Forms.MouseEventHandler(this.panelInnerMinimap_MouseUp);
            // 
            // miniViewPanel
            // 
            this.miniViewPanel.AutoSizeMode = System.Windows.Forms.AutoSizeMode.GrowAndShrink;
            this.miniViewPanel.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
            this.miniViewPanel.Location = new System.Drawing.Point(3, 3);
            this.miniViewPanel.Name = "miniViewPanel";
            this.miniViewPanel.Size = new System.Drawing.Size(561, 534);
            this.miniViewPanel.TabIndex = 1;
            this.miniViewPanel.Paint += new System.Windows.Forms.PaintEventHandler(this.miniViewPanel_Paint);
            this.miniViewPanel.MouseDoubleClick += new System.Windows.Forms.MouseEventHandler(this.miniViewPanel_MouseDoubleClick);
            this.miniViewPanel.MouseDown += new System.Windows.Forms.MouseEventHandler(this.miniViewPanel_MouseDown);
            this.miniViewPanel.MouseMove += new System.Windows.Forms.MouseEventHandler(this.miniViewPanel_MouseMove);
            this.miniViewPanel.MouseUp += new System.Windows.Forms.MouseEventHandler(this.miniViewPanel_MouseUp);
            this.miniViewPanel.Resize += new System.EventHandler(this.miniViewPanel_Resize);
            // 
            // groupMiniMapTab
            // 
            this.groupMiniMapTab.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Center;
            this.groupMiniMapTab.Controls.Add(this.cmdDebug);
            this.groupMiniMapTab.Controls.Add(this.MiniEditPanel);
            this.groupMiniMapTab.Controls.Add(this.miniEdit);
            this.groupMiniMapTab.Controls.Add(this.label5);
            this.groupMiniMapTab.Controls.Add(this.numMinimapZoom);
            this.groupMiniMapTab.Controls.Add(this.chkDivide2);
            this.groupMiniMapTab.Controls.Add(this.chkDivide);
            this.groupMiniMapTab.Controls.Add(this.cmdGoToCenter);
            this.groupMiniMapTab.Dock = System.Windows.Forms.DockStyle.Left;
            this.groupMiniMapTab.Location = new System.Drawing.Point(0, 0);
            this.groupMiniMapTab.Name = "groupMiniMapTab";
            this.groupMiniMapTab.Size = new System.Drawing.Size(120, 691);
            this.groupMiniMapTab.TabIndex = 0;
            this.groupMiniMapTab.TabStop = false;
            // 
            // cmdDebug
            // 
            this.cmdDebug.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.cmdDebug.Location = new System.Drawing.Point(14, 652);
            this.cmdDebug.Name = "cmdDebug";
            this.cmdDebug.Size = new System.Drawing.Size(84, 23);
            this.cmdDebug.TabIndex = 14;
            this.cmdDebug.Text = "Debug";
            this.cmdDebug.UseVisualStyleBackColor = true;
            this.cmdDebug.Visible = false;
            // 
            // MiniEditPanel
            // 
            this.MiniEditPanel.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
            this.MiniEditPanel.Controls.Add(this.label10);
            this.MiniEditPanel.Controls.Add(this.cmdPolygons);
            this.MiniEditPanel.Controls.Add(this.label9);
            this.MiniEditPanel.Controls.Add(this.miniRedo);
            this.MiniEditPanel.Controls.Add(this.miniUndo);
            this.MiniEditPanel.Controls.Add(this.miniLineWall);
            this.MiniEditPanel.Controls.Add(this.label8);
            this.MiniEditPanel.Controls.Add(this.label7);
            this.MiniEditPanel.Controls.Add(this.label6);
            this.MiniEditPanel.Controls.Add(this.numBrushSize);
            this.MiniEditPanel.Controls.Add(this.miniTileBrush);
            this.MiniEditPanel.Controls.Add(this.miniTilePLace);
            this.MiniEditPanel.Controls.Add(this.miniWallBrush);
            this.MiniEditPanel.Controls.Add(this.labelSep2);
            this.MiniEditPanel.Enabled = false;
            this.MiniEditPanel.Location = new System.Drawing.Point(8, 78);
            this.MiniEditPanel.Name = "MiniEditPanel";
            this.MiniEditPanel.Size = new System.Drawing.Size(102, 287);
            this.MiniEditPanel.TabIndex = 12;
            // 
            // label10
            // 
            this.label10.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
            this.label10.Location = new System.Drawing.Point(0, 241);
            this.label10.Name = "label10";
            this.label10.Size = new System.Drawing.Size(99, 2);
            this.label10.TabIndex = 35;
            // 
            // cmdPolygons
            // 
            this.cmdPolygons.Location = new System.Drawing.Point(16, 252);
            this.cmdPolygons.Name = "cmdPolygons";
            this.cmdPolygons.Size = new System.Drawing.Size(66, 23);
            this.cmdPolygons.TabIndex = 34;
            this.cmdPolygons.Text = "Polygons";
            this.cmdPolygons.UseVisualStyleBackColor = true;
            this.cmdPolygons.Click += new System.EventHandler(this.cmdPolygons_Click);
            // 
            // label9
            // 
            this.label9.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
            this.label9.Location = new System.Drawing.Point(0, 29);
            this.label9.Name = "label9";
            this.label9.Size = new System.Drawing.Size(99, 2);
            this.label9.TabIndex = 33;
            // 
            // miniRedo
            // 
            this.miniRedo.BackgroundImage = global::MapEditor.Properties.Resources.redoDisabled;
            this.miniRedo.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Stretch;
            this.miniRedo.Enabled = false;
            this.miniRedo.Location = new System.Drawing.Point(49, 1);
            this.miniRedo.Name = "miniRedo";
            this.miniRedo.Size = new System.Drawing.Size(25, 25);
            this.miniRedo.TabIndex = 32;
            this.miniRedo.UseVisualStyleBackColor = true;
            this.miniRedo.EnabledChanged += new System.EventHandler(this.miniRedo_EnabledChanged);
            this.miniRedo.Click += new System.EventHandler(this.miniRedo_Click);
            // 
            // miniUndo
            // 
            this.miniUndo.BackgroundImage = global::MapEditor.Properties.Resources.undoDisabled;
            this.miniUndo.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Stretch;
            this.miniUndo.Enabled = false;
            this.miniUndo.Location = new System.Drawing.Point(25, 1);
            this.miniUndo.Name = "miniUndo";
            this.miniUndo.Size = new System.Drawing.Size(25, 25);
            this.miniUndo.TabIndex = 31;
            this.miniUndo.UseVisualStyleBackColor = true;
            this.miniUndo.EnabledChanged += new System.EventHandler(this.miniUndo_EnabledChanged);
            this.miniUndo.Click += new System.EventHandler(this.miniUndo_Click);
            // 
            // miniLineWall
            // 
            this.miniLineWall.Appearance = System.Windows.Forms.Appearance.Button;
            this.miniLineWall.BackgroundImage = global::MapEditor.Properties.Resources.LineWall;
            this.miniLineWall.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Center;
            this.miniLineWall.Location = new System.Drawing.Point(10, 79);
            this.miniLineWall.Name = "miniLineWall";
            this.miniLineWall.Size = new System.Drawing.Size(25, 25);
            this.miniLineWall.TabIndex = 27;
            this.miniLineWall.UseVisualStyleBackColor = true;
            this.miniLineWall.Visible = false;
            this.miniLineWall.CheckedChanged += new System.EventHandler(this.miniLineWall_CheckedChanged);
            // 
            // label8
            // 
            this.label8.AutoSize = true;
            this.label8.Location = new System.Drawing.Point(22, 196);
            this.label8.Name = "label8";
            this.label8.Size = new System.Drawing.Size(58, 13);
            this.label8.TabIndex = 26;
            this.label8.Text = "Brush size:";
            // 
            // label7
            // 
            this.label7.AutoSize = true;
            this.label7.Location = new System.Drawing.Point(20, 117);
            this.label7.Name = "label7";
            this.label7.Size = new System.Drawing.Size(58, 13);
            this.label7.TabIndex = 25;
            this.label7.Text = "Tile editing";
            // 
            // label6
            // 
            this.label6.AutoSize = true;
            this.label6.Location = new System.Drawing.Point(17, 34);
            this.label6.Name = "label6";
            this.label6.Size = new System.Drawing.Size(62, 13);
            this.label6.TabIndex = 24;
            this.label6.Text = "Wall editing";
            // 
            // numBrushSize
            // 
            this.numBrushSize.Location = new System.Drawing.Point(28, 213);
            this.numBrushSize.Maximum = new decimal(new int[] {
            6,
            0,
            0,
            0});
            this.numBrushSize.Minimum = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.numBrushSize.Name = "numBrushSize";
            this.numBrushSize.Size = new System.Drawing.Size(48, 20);
            this.numBrushSize.TabIndex = 23;
            this.numBrushSize.Value = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.numBrushSize.ValueChanged += new System.EventHandler(this.numBrushSize_ValueChanged);
            // 
            // miniTileBrush
            // 
            this.miniTileBrush.Appearance = System.Windows.Forms.Appearance.Button;
            this.miniTileBrush.FlatStyle = System.Windows.Forms.FlatStyle.System;
            this.miniTileBrush.Location = new System.Drawing.Point(10, 162);
            this.miniTileBrush.Name = "miniTileBrush";
            this.miniTileBrush.Size = new System.Drawing.Size(80, 25);
            this.miniTileBrush.TabIndex = 22;
            this.miniTileBrush.TabStop = true;
            this.miniTileBrush.Text = "Tile Brush";
            this.miniTileBrush.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            this.miniTileBrush.UseVisualStyleBackColor = true;
            this.miniTileBrush.CheckedChanged += new System.EventHandler(this.miniTileBrush_CheckedChanged);
            // 
            // miniTilePLace
            // 
            this.miniTilePLace.Appearance = System.Windows.Forms.Appearance.Button;
            this.miniTilePLace.FlatStyle = System.Windows.Forms.FlatStyle.System;
            this.miniTilePLace.Location = new System.Drawing.Point(10, 135);
            this.miniTilePLace.Name = "miniTilePLace";
            this.miniTilePLace.Size = new System.Drawing.Size(80, 25);
            this.miniTilePLace.TabIndex = 21;
            this.miniTilePLace.TabStop = true;
            this.miniTilePLace.Text = "Tile Place";
            this.miniTilePLace.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            this.miniTilePLace.UseVisualStyleBackColor = true;
            this.miniTilePLace.CheckedChanged += new System.EventHandler(this.miniTilePLace_CheckedChanged);
            // 
            // miniWallBrush
            // 
            this.miniWallBrush.Appearance = System.Windows.Forms.Appearance.Button;
            this.miniWallBrush.FlatStyle = System.Windows.Forms.FlatStyle.System;
            this.miniWallBrush.Location = new System.Drawing.Point(10, 52);
            this.miniWallBrush.Name = "miniWallBrush";
            this.miniWallBrush.Size = new System.Drawing.Size(80, 25);
            this.miniWallBrush.TabIndex = 20;
            this.miniWallBrush.TabStop = true;
            this.miniWallBrush.Text = "Wall Brush";
            this.miniWallBrush.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            this.miniWallBrush.UseVisualStyleBackColor = true;
            this.miniWallBrush.CheckedChanged += new System.EventHandler(this.miniWallBrush_CheckedChanged);
            // 
            // labelSep2
            // 
            this.labelSep2.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
            this.labelSep2.Location = new System.Drawing.Point(0, 111);
            this.labelSep2.Name = "labelSep2";
            this.labelSep2.Size = new System.Drawing.Size(99, 2);
            this.labelSep2.TabIndex = 18;
            // 
            // miniEdit
            // 
            this.miniEdit.AutoSize = true;
            this.miniEdit.Location = new System.Drawing.Point(12, 55);
            this.miniEdit.Name = "miniEdit";
            this.miniEdit.Size = new System.Drawing.Size(87, 17);
            this.miniEdit.TabIndex = 10;
            this.miniEdit.Text = "Editing mode";
            this.miniEdit.UseVisualStyleBackColor = true;
            this.miniEdit.CheckedChanged += new System.EventHandler(this.miniEdit_CheckedChanged);
            // 
            // label5
            // 
            this.label5.AutoSize = true;
            this.label5.Location = new System.Drawing.Point(9, 26);
            this.label5.Name = "label5";
            this.label5.Size = new System.Drawing.Size(37, 13);
            this.label5.TabIndex = 9;
            this.label5.Text = "Zoom:";
            // 
            // numMinimapZoom
            // 
            this.numMinimapZoom.Location = new System.Drawing.Point(52, 23);
            this.numMinimapZoom.Maximum = new decimal(new int[] {
            7,
            0,
            0,
            0});
            this.numMinimapZoom.Minimum = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.numMinimapZoom.Name = "numMinimapZoom";
            this.numMinimapZoom.Size = new System.Drawing.Size(48, 20);
            this.numMinimapZoom.TabIndex = 4;
            this.numMinimapZoom.Value = new decimal(new int[] {
            2,
            0,
            0,
            0});
            this.numMinimapZoom.ValueChanged += new System.EventHandler(this.numMinimapZoom_ValueChanged);
            // 
            // chkDivide2
            // 
            this.chkDivide2.AutoSize = true;
            this.chkDivide2.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.chkDivide2.Location = new System.Drawing.Point(14, 403);
            this.chkDivide2.Name = "chkDivide2";
            this.chkDivide2.Size = new System.Drawing.Size(62, 17);
            this.chkDivide2.TabIndex = 7;
            this.chkDivide2.Text = "Divide2";
            this.chkDivide2.UseVisualStyleBackColor = true;
            this.chkDivide2.CheckedChanged += new System.EventHandler(this.chkDivide2_CheckedChanged);
            // 
            // chkDivide
            // 
            this.chkDivide.AutoSize = true;
            this.chkDivide.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.chkDivide.Location = new System.Drawing.Point(14, 380);
            this.chkDivide.Name = "chkDivide";
            this.chkDivide.Size = new System.Drawing.Size(62, 17);
            this.chkDivide.TabIndex = 6;
            this.chkDivide.Text = "Divide1";
            this.chkDivide.UseVisualStyleBackColor = true;
            this.chkDivide.CheckedChanged += new System.EventHandler(this.chkDivide_CheckedChanged);
            // 
            // cmdGoToCenter
            // 
            this.cmdGoToCenter.ImeMode = System.Windows.Forms.ImeMode.NoControl;
            this.cmdGoToCenter.Location = new System.Drawing.Point(8, 426);
            this.cmdGoToCenter.Name = "cmdGoToCenter";
            this.cmdGoToCenter.Size = new System.Drawing.Size(84, 23);
            this.cmdGoToCenter.TabIndex = 2;
            this.cmdGoToCenter.Text = "Go to Center";
            this.cmdGoToCenter.UseVisualStyleBackColor = true;
            this.cmdGoToCenter.Click += new System.EventHandler(this.cmdGoToCenter_Click);
            // 
            // largeMap
            // 
            this.largeMap.Controls.Add(this.suggestBox);
            this.largeMap.Controls.Add(this.mapView);
            this.largeMap.Location = new System.Drawing.Point(4, 22);
            this.largeMap.Name = "largeMap";
            this.largeMap.Size = new System.Drawing.Size(1000, 691);
            this.largeMap.TabIndex = 0;
            this.largeMap.Text = "Large Map";
            this.largeMap.UseVisualStyleBackColor = true;
            // 
            // suggestBox
            // 
            this.suggestBox.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.suggestBox.FormattingEnabled = true;
            this.suggestBox.Location = new System.Drawing.Point(208, 226);
            this.suggestBox.Name = "suggestBox";
            this.suggestBox.Size = new System.Drawing.Size(159, 80);
            this.suggestBox.TabIndex = 1;
            this.suggestBox.Visible = false;
            this.suggestBox.MouseClick += new System.Windows.Forms.MouseEventHandler(this.suggestBox_MouseClick);
            this.suggestBox.MouseEnter += new System.EventHandler(this.suggestBox_MouseEnter);
            this.suggestBox.MouseLeave += new System.EventHandler(this.suggestBox_MouseLeave);
            this.suggestBox.MouseMove += new System.Windows.Forms.MouseEventHandler(this.suggestBox_MouseMove);
            // 
            // mapView
            // 
            this.mapView.Dock = System.Windows.Forms.DockStyle.Fill;
            this.mapView.Location = new System.Drawing.Point(0, 0);
            this.mapView.Name = "mapView";
            this.mapView.Size = new System.Drawing.Size(1000, 691);
            this.mapView.TabIndex = 0;
            // 
            // panelTabs
            // 
            this.panelTabs.Controls.Add(this.largeMap);
            this.panelTabs.Controls.Add(this.minimapTab);
            this.panelTabs.Controls.Add(this.mapInfoTab);
            this.panelTabs.Controls.Add(this.mapImageTab);
            this.panelTabs.Dock = System.Windows.Forms.DockStyle.Fill;
            this.panelTabs.ItemSize = new System.Drawing.Size(63, 18);
            this.panelTabs.Location = new System.Drawing.Point(0, 24);
            this.panelTabs.Name = "panelTabs";
            this.panelTabs.SelectedIndex = 0;
            this.panelTabs.Size = new System.Drawing.Size(1008, 717);
            this.panelTabs.TabIndex = 0;
            this.panelTabs.MouseClick += new System.Windows.Forms.MouseEventHandler(this.panelTabs_MouseClick);
            // 
            // mapImageTab
            // 
            this.mapImageTab.Controls.Add(this.cmdImgRender);
            this.mapImageTab.Controls.Add(this.groupImgExport);
            this.mapImageTab.Controls.Add(this.cmdImgExport);
            this.mapImageTab.Controls.Add(this.groupImgEntities);
            this.mapImageTab.Controls.Add(this.progBarImage);
            this.mapImageTab.Controls.Add(this.groupImgObjects);
            this.mapImageTab.Controls.Add(this.chkImgUseCurrentSettings);
            this.mapImageTab.Controls.Add(this.picMapImage);
            this.mapImageTab.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.mapImageTab.Location = new System.Drawing.Point(4, 22);
            this.mapImageTab.Name = "mapImageTab";
            this.mapImageTab.Padding = new System.Windows.Forms.Padding(3);
            this.mapImageTab.Size = new System.Drawing.Size(1000, 691);
            this.mapImageTab.TabIndex = 1;
            this.mapImageTab.Text = "Map Image";
            this.mapImageTab.UseVisualStyleBackColor = true;
            // 
            // cmdImgRender
            // 
            this.cmdImgRender.Location = new System.Drawing.Point(9, 47);
            this.cmdImgRender.Name = "cmdImgRender";
            this.cmdImgRender.Size = new System.Drawing.Size(103, 35);
            this.cmdImgRender.TabIndex = 9;
            this.cmdImgRender.Text = "Render";
            this.cmdImgRender.UseVisualStyleBackColor = true;
            this.cmdImgRender.Click += new System.EventHandler(this.cmdImgRender_Click);
            // 
            // groupImgExport
            // 
            this.groupImgExport.Controls.Add(this.chkImgBackground);
            this.groupImgExport.Controls.Add(this.lblImgDimensions);
            this.groupImgExport.Controls.Add(this.trackImgSize);
            this.groupImgExport.Controls.Add(this.numImgPadding);
            this.groupImgExport.Controls.Add(this.lblImgPadding);
            this.groupImgExport.Controls.Add(this.chkImgAutoCrop);
            this.groupImgExport.Controls.Add(this.lblImgSize);
            this.groupImgExport.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupImgExport.Location = new System.Drawing.Point(5, 88);
            this.groupImgExport.Name = "groupImgExport";
            this.groupImgExport.Size = new System.Drawing.Size(220, 155);
            this.groupImgExport.TabIndex = 5;
            this.groupImgExport.TabStop = false;
            this.groupImgExport.Text = " Image ";
            // 
            // chkImgBackground
            // 
            this.chkImgBackground.AutoSize = true;
            this.chkImgBackground.Checked = true;
            this.chkImgBackground.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgBackground.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgBackground.Location = new System.Drawing.Point(97, 25);
            this.chkImgBackground.Name = "chkImgBackground";
            this.chkImgBackground.Size = new System.Drawing.Size(100, 20);
            this.chkImgBackground.TabIndex = 7;
            this.chkImgBackground.Text = "Background";
            this.chkImgBackground.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            this.chkImgBackground.UseVisualStyleBackColor = true;
            // 
            // lblImgDimensions
            // 
            this.lblImgDimensions.Font = new System.Drawing.Font("Microsoft Sans Serif", 9F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lblImgDimensions.Location = new System.Drawing.Point(54, 78);
            this.lblImgDimensions.Name = "lblImgDimensions";
            this.lblImgDimensions.Size = new System.Drawing.Size(152, 18);
            this.lblImgDimensions.TabIndex = 6;
            this.lblImgDimensions.Text = "5880 x 5880  (100%)";
            this.lblImgDimensions.TextAlign = System.Drawing.ContentAlignment.TopCenter;
            // 
            // trackImgSize
            // 
            this.trackImgSize.Location = new System.Drawing.Point(12, 97);
            this.trackImgSize.Maximum = 100;
            this.trackImgSize.Minimum = 1;
            this.trackImgSize.Name = "trackImgSize";
            this.trackImgSize.RightToLeft = System.Windows.Forms.RightToLeft.No;
            this.trackImgSize.Size = new System.Drawing.Size(194, 45);
            this.trackImgSize.TabIndex = 5;
            this.trackImgSize.TickFrequency = 5;
            this.trackImgSize.TickStyle = System.Windows.Forms.TickStyle.Both;
            this.trackImgSize.Value = 100;
            this.trackImgSize.Scroll += new System.EventHandler(this.trackImgSize_Scroll);
            // 
            // numImgPadding
            // 
            this.numImgPadding.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.numImgPadding.Increment = new decimal(new int[] {
            5,
            0,
            0,
            0});
            this.numImgPadding.Location = new System.Drawing.Point(104, 50);
            this.numImgPadding.Maximum = new decimal(new int[] {
            1000,
            0,
            0,
            0});
            this.numImgPadding.Name = "numImgPadding";
            this.numImgPadding.Size = new System.Drawing.Size(64, 22);
            this.numImgPadding.TabIndex = 3;
            this.numImgPadding.Value = new decimal(new int[] {
            10,
            0,
            0,
            0});
            // 
            // lblImgPadding
            // 
            this.lblImgPadding.AutoSize = true;
            this.lblImgPadding.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lblImgPadding.Location = new System.Drawing.Point(43, 52);
            this.lblImgPadding.Name = "lblImgPadding";
            this.lblImgPadding.Size = new System.Drawing.Size(62, 16);
            this.lblImgPadding.TabIndex = 2;
            this.lblImgPadding.Text = "Padding:";
            // 
            // chkImgAutoCrop
            // 
            this.chkImgAutoCrop.AutoSize = true;
            this.chkImgAutoCrop.Checked = true;
            this.chkImgAutoCrop.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgAutoCrop.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgAutoCrop.Location = new System.Drawing.Point(34, 25);
            this.chkImgAutoCrop.Name = "chkImgAutoCrop";
            this.chkImgAutoCrop.Size = new System.Drawing.Size(56, 20);
            this.chkImgAutoCrop.TabIndex = 1;
            this.chkImgAutoCrop.Text = "Crop";
            this.chkImgAutoCrop.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            this.chkImgAutoCrop.UseVisualStyleBackColor = true;
            this.chkImgAutoCrop.CheckedChanged += new System.EventHandler(this.chkImgAutoCrop_CheckedChanged);
            // 
            // lblImgSize
            // 
            this.lblImgSize.AutoSize = true;
            this.lblImgSize.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lblImgSize.Location = new System.Drawing.Point(21, 78);
            this.lblImgSize.Name = "lblImgSize";
            this.lblImgSize.Size = new System.Drawing.Size(37, 16);
            this.lblImgSize.TabIndex = 4;
            this.lblImgSize.Text = "Size:";
            // 
            // cmdImgExport
            // 
            this.cmdImgExport.Enabled = false;
            this.cmdImgExport.Location = new System.Drawing.Point(114, 47);
            this.cmdImgExport.Name = "cmdImgExport";
            this.cmdImgExport.Size = new System.Drawing.Size(103, 35);
            this.cmdImgExport.TabIndex = 8;
            this.cmdImgExport.Text = "Export";
            this.cmdImgExport.UseVisualStyleBackColor = true;
            this.cmdImgExport.Click += new System.EventHandler(this.cmdImgExport_Click);
            // 
            // groupImgEntities
            // 
            this.groupImgEntities.Controls.Add(this.chkImgBroken);
            this.groupImgEntities.Controls.Add(this.chkImgBoss);
            this.groupImgEntities.Controls.Add(this.chkImgAmbient);
            this.groupImgEntities.Controls.Add(this.chkImgHard);
            this.groupImgEntities.Controls.Add(this.chkImgEasy);
            this.groupImgEntities.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupImgEntities.Location = new System.Drawing.Point(5, 410);
            this.groupImgEntities.Name = "groupImgEntities";
            this.groupImgEntities.Size = new System.Drawing.Size(220, 95);
            this.groupImgEntities.TabIndex = 4;
            this.groupImgEntities.TabStop = false;
            this.groupImgEntities.Text = " Entities ";
            // 
            // chkImgBroken
            // 
            this.chkImgBroken.AutoSize = true;
            this.chkImgBroken.Checked = true;
            this.chkImgBroken.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgBroken.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgBroken.Location = new System.Drawing.Point(111, 25);
            this.chkImgBroken.Name = "chkImgBroken";
            this.chkImgBroken.Size = new System.Drawing.Size(70, 20);
            this.chkImgBroken.TabIndex = 4;
            this.chkImgBroken.Text = "Broken";
            this.chkImgBroken.UseVisualStyleBackColor = true;
            // 
            // chkImgBoss
            // 
            this.chkImgBoss.AutoSize = true;
            this.chkImgBoss.Checked = true;
            this.chkImgBoss.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgBoss.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgBoss.Location = new System.Drawing.Point(25, 65);
            this.chkImgBoss.Name = "chkImgBoss";
            this.chkImgBoss.Size = new System.Drawing.Size(58, 20);
            this.chkImgBoss.TabIndex = 3;
            this.chkImgBoss.Text = "Boss";
            this.chkImgBoss.UseVisualStyleBackColor = true;
            // 
            // chkImgAmbient
            // 
            this.chkImgAmbient.AutoSize = true;
            this.chkImgAmbient.Checked = true;
            this.chkImgAmbient.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgAmbient.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgAmbient.Location = new System.Drawing.Point(111, 45);
            this.chkImgAmbient.Name = "chkImgAmbient";
            this.chkImgAmbient.Size = new System.Drawing.Size(76, 20);
            this.chkImgAmbient.TabIndex = 2;
            this.chkImgAmbient.Text = "Ambient";
            this.chkImgAmbient.UseVisualStyleBackColor = true;
            // 
            // chkImgHard
            // 
            this.chkImgHard.AutoSize = true;
            this.chkImgHard.Checked = true;
            this.chkImgHard.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgHard.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgHard.Location = new System.Drawing.Point(25, 45);
            this.chkImgHard.Name = "chkImgHard";
            this.chkImgHard.Size = new System.Drawing.Size(57, 20);
            this.chkImgHard.TabIndex = 1;
            this.chkImgHard.Text = "Hard";
            this.chkImgHard.UseVisualStyleBackColor = true;
            // 
            // chkImgEasy
            // 
            this.chkImgEasy.AutoSize = true;
            this.chkImgEasy.Checked = true;
            this.chkImgEasy.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgEasy.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgEasy.Location = new System.Drawing.Point(25, 25);
            this.chkImgEasy.Name = "chkImgEasy";
            this.chkImgEasy.Size = new System.Drawing.Size(58, 20);
            this.chkImgEasy.TabIndex = 0;
            this.chkImgEasy.Text = "Easy";
            this.chkImgEasy.UseVisualStyleBackColor = true;
            // 
            // progBarImage
            // 
            this.progBarImage.Location = new System.Drawing.Point(3, 10);
            this.progBarImage.Name = "progBarImage";
            this.progBarImage.Size = new System.Drawing.Size(222, 28);
            this.progBarImage.Step = 1;
            this.progBarImage.TabIndex = 3;
            // 
            // groupImgObjects
            // 
            this.groupImgObjects.Controls.Add(this.chkImgQuest);
            this.groupImgObjects.Controls.Add(this.chkImgChests);
            this.groupImgObjects.Controls.Add(this.chkImgFood);
            this.groupImgObjects.Controls.Add(this.chkImgWeapons);
            this.groupImgObjects.Controls.Add(this.chkImgCrystals);
            this.groupImgObjects.Controls.Add(this.chkImgGold);
            this.groupImgObjects.Controls.Add(this.chkImgPotions);
            this.groupImgObjects.Controls.Add(this.chkImgArmor);
            this.groupImgObjects.Font = new System.Drawing.Font("Microsoft Sans Serif", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupImgObjects.Location = new System.Drawing.Point(5, 288);
            this.groupImgObjects.Name = "groupImgObjects";
            this.groupImgObjects.Size = new System.Drawing.Size(220, 116);
            this.groupImgObjects.TabIndex = 2;
            this.groupImgObjects.TabStop = false;
            this.groupImgObjects.Text = " Objects ";
            // 
            // chkImgQuest
            // 
            this.chkImgQuest.AutoSize = true;
            this.chkImgQuest.Checked = true;
            this.chkImgQuest.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgQuest.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgQuest.Location = new System.Drawing.Point(111, 85);
            this.chkImgQuest.Name = "chkImgQuest";
            this.chkImgQuest.Size = new System.Drawing.Size(62, 20);
            this.chkImgQuest.TabIndex = 7;
            this.chkImgQuest.Text = "Quest";
            this.chkImgQuest.UseVisualStyleBackColor = true;
            // 
            // chkImgChests
            // 
            this.chkImgChests.AutoSize = true;
            this.chkImgChests.Checked = true;
            this.chkImgChests.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgChests.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgChests.Location = new System.Drawing.Point(111, 65);
            this.chkImgChests.Name = "chkImgChests";
            this.chkImgChests.Size = new System.Drawing.Size(68, 20);
            this.chkImgChests.TabIndex = 6;
            this.chkImgChests.Text = "Chests";
            this.chkImgChests.UseVisualStyleBackColor = true;
            // 
            // chkImgFood
            // 
            this.chkImgFood.AutoSize = true;
            this.chkImgFood.Checked = true;
            this.chkImgFood.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgFood.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgFood.Location = new System.Drawing.Point(111, 45);
            this.chkImgFood.Name = "chkImgFood";
            this.chkImgFood.Size = new System.Drawing.Size(59, 20);
            this.chkImgFood.TabIndex = 5;
            this.chkImgFood.Text = "Food";
            this.chkImgFood.UseVisualStyleBackColor = true;
            // 
            // chkImgWeapons
            // 
            this.chkImgWeapons.AutoSize = true;
            this.chkImgWeapons.Checked = true;
            this.chkImgWeapons.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgWeapons.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgWeapons.Location = new System.Drawing.Point(111, 25);
            this.chkImgWeapons.Name = "chkImgWeapons";
            this.chkImgWeapons.Size = new System.Drawing.Size(86, 20);
            this.chkImgWeapons.TabIndex = 4;
            this.chkImgWeapons.Text = "Weapons";
            this.chkImgWeapons.UseVisualStyleBackColor = true;
            // 
            // chkImgCrystals
            // 
            this.chkImgCrystals.AutoSize = true;
            this.chkImgCrystals.Checked = true;
            this.chkImgCrystals.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgCrystals.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgCrystals.Location = new System.Drawing.Point(25, 65);
            this.chkImgCrystals.Name = "chkImgCrystals";
            this.chkImgCrystals.Size = new System.Drawing.Size(75, 20);
            this.chkImgCrystals.TabIndex = 3;
            this.chkImgCrystals.Text = "Crystals";
            this.chkImgCrystals.UseVisualStyleBackColor = true;
            // 
            // chkImgGold
            // 
            this.chkImgGold.AutoSize = true;
            this.chkImgGold.Checked = true;
            this.chkImgGold.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgGold.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgGold.Location = new System.Drawing.Point(25, 85);
            this.chkImgGold.Name = "chkImgGold";
            this.chkImgGold.Size = new System.Drawing.Size(56, 20);
            this.chkImgGold.TabIndex = 2;
            this.chkImgGold.Text = "Gold";
            this.chkImgGold.UseVisualStyleBackColor = true;
            // 
            // chkImgPotions
            // 
            this.chkImgPotions.AutoSize = true;
            this.chkImgPotions.Checked = true;
            this.chkImgPotions.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgPotions.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgPotions.Location = new System.Drawing.Point(25, 45);
            this.chkImgPotions.Name = "chkImgPotions";
            this.chkImgPotions.Size = new System.Drawing.Size(72, 20);
            this.chkImgPotions.TabIndex = 1;
            this.chkImgPotions.Text = "Potions";
            this.chkImgPotions.UseVisualStyleBackColor = true;
            // 
            // chkImgArmor
            // 
            this.chkImgArmor.AutoSize = true;
            this.chkImgArmor.Checked = true;
            this.chkImgArmor.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkImgArmor.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgArmor.Location = new System.Drawing.Point(25, 25);
            this.chkImgArmor.Name = "chkImgArmor";
            this.chkImgArmor.Size = new System.Drawing.Size(63, 20);
            this.chkImgArmor.TabIndex = 0;
            this.chkImgArmor.Text = "Armor";
            this.chkImgArmor.UseVisualStyleBackColor = true;
            // 
            // chkImgUseCurrentSettings
            // 
            this.chkImgUseCurrentSettings.Appearance = System.Windows.Forms.Appearance.Button;
            this.chkImgUseCurrentSettings.AutoSize = true;
            this.chkImgUseCurrentSettings.FlatStyle = System.Windows.Forms.FlatStyle.System;
            this.chkImgUseCurrentSettings.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkImgUseCurrentSettings.Location = new System.Drawing.Point(40, 255);
            this.chkImgUseCurrentSettings.Name = "chkImgUseCurrentSettings";
            this.chkImgUseCurrentSettings.Size = new System.Drawing.Size(139, 26);
            this.chkImgUseCurrentSettings.TabIndex = 1;
            this.chkImgUseCurrentSettings.Text = "Use Current Settings";
            this.chkImgUseCurrentSettings.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            this.chkImgUseCurrentSettings.UseVisualStyleBackColor = true;
            this.chkImgUseCurrentSettings.CheckedChanged += new System.EventHandler(this.chkImgUseCurrentSettings_CheckedChanged);
            // 
            // picMapImage
            // 
            this.picMapImage.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.picMapImage.BackgroundImage = global::MapEditor.Properties.Resources.transTile;
            this.picMapImage.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.picMapImage.Location = new System.Drawing.Point(234, 4);
            this.picMapImage.Name = "picMapImage";
            this.picMapImage.Size = new System.Drawing.Size(763, 682);
            this.picMapImage.TabIndex = 0;
            this.picMapImage.TabStop = false;
            // 
            // mainMenuStrip
            // 
            this.mainMenuStrip.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.menuFile,
            this.menuMap,
            this.menuOptions,
            this.menuHelp,
            this.menuShortcuts});
            this.mainMenuStrip.Location = new System.Drawing.Point(0, 0);
            this.mainMenuStrip.Name = "mainMenuStrip";
            this.mainMenuStrip.Size = new System.Drawing.Size(1008, 24);
            this.mainMenuStrip.TabIndex = 1;
            this.mainMenuStrip.Text = "menuStrip1";
            // 
            // menuFile
            // 
            this.menuFile.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.menuNew,
            this.menuOpen,
            this.menuRecent,
            this.menuInstallMap,
            this.menuSave,
            this.menuSaveAs,
            this.menuSaveNXZOnly,
            this.toolStripSeparator1,
            this.menuImportSave,
            this.menuImportScript,
            this.menuExportScript,
            this.menuExportNativeScript,
            this.toolStripSeparator2,
            this.menuExit});
            this.menuFile.Name = "menuFile";
            this.menuFile.Size = new System.Drawing.Size(37, 20);
            this.menuFile.Text = "&File";
            // 
            // menuNew
            // 
            this.menuNew.Name = "menuNew";
            this.menuNew.Size = new System.Drawing.Size(189, 22);
            this.menuNew.Text = "New";
            this.menuNew.Click += new System.EventHandler(this.menuNew_Click);
            // 
            // menuOpen
            // 
            this.menuOpen.Name = "menuOpen";
            this.menuOpen.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.O)));
            this.menuOpen.Size = new System.Drawing.Size(189, 22);
            this.menuOpen.Text = "Open...";
            this.menuOpen.Click += new System.EventHandler(this.menuOpen_Click);
            // 
            // menuRecent
            // 
            this.menuRecent.Name = "menuRecent";
            this.menuRecent.Size = new System.Drawing.Size(189, 22);
            this.menuRecent.Text = "Recent";
            this.menuRecent.DropDownItemClicked += new System.Windows.Forms.ToolStripItemClickedEventHandler(this.menuRecent_DropDownItemClicked);
            // 
            // menuInstallMap
            // 
            this.menuInstallMap.Name = "menuInstallMap";
            this.menuInstallMap.Size = new System.Drawing.Size(189, 22);
            this.menuInstallMap.Text = "Install Map";
            this.menuInstallMap.Click += new System.EventHandler(this.menuInstallMap_Click);
            // 
            // menuSave
            // 
            this.menuSave.Name = "menuSave";
            this.menuSave.ShortcutKeys = System.Windows.Forms.Keys.F2;
            this.menuSave.Size = new System.Drawing.Size(189, 22);
            this.menuSave.Text = "Save";
            this.menuSave.Click += new System.EventHandler(this.menuSave_Click);
            // 
            // menuSaveAs
            // 
            this.menuSaveAs.Name = "menuSaveAs";
            this.menuSaveAs.ShortcutKeys = System.Windows.Forms.Keys.F3;
            this.menuSaveAs.Size = new System.Drawing.Size(189, 22);
            this.menuSaveAs.Text = "Save As...";
            this.menuSaveAs.Click += new System.EventHandler(this.menuSaveAs_Click);
            // 
            // menuSaveNXZOnly
            // 
            this.menuSaveNXZOnly.Name = "menuSaveNXZOnly";
            this.menuSaveNXZOnly.Size = new System.Drawing.Size(189, 22);
            this.menuSaveNXZOnly.Text = "Save NXZ Only";
            this.menuSaveNXZOnly.Click += new System.EventHandler(this.menuSaveNXZOnly_Click);
            // 
            // toolStripSeparator1
            // 
            this.toolStripSeparator1.Name = "toolStripSeparator1";
            this.toolStripSeparator1.Size = new System.Drawing.Size(186, 6);
            // 
            // menuImportSave
            // 
            this.menuImportSave.Enabled = false;
            this.menuImportSave.Name = "menuImportSave";
            this.menuImportSave.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.S)));
            this.menuImportSave.Size = new System.Drawing.Size(189, 22);
            this.menuImportSave.Text = "Import + Save";
            this.menuImportSave.Click += new System.EventHandler(this.menuImportSave_Click);
            // 
            // menuImportScript
            // 
            this.menuImportScript.Name = "menuImportScript";
            this.menuImportScript.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.I)));
            this.menuImportScript.Size = new System.Drawing.Size(189, 22);
            this.menuImportScript.Text = "Import Script...";
            this.menuImportScript.Click += new System.EventHandler(this.menuImportScript_Click);
            // 
            // menuExportScript
            // 
            this.menuExportScript.Name = "menuExportScript";
            this.menuExportScript.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.E)));
            this.menuExportScript.Size = new System.Drawing.Size(189, 22);
            this.menuExportScript.Text = "Export Script...";
            this.menuExportScript.Click += new System.EventHandler(this.menuExportScript_Click);
            // 
            // menuExportNativeScript
            // 
            this.menuExportNativeScript.Name = "menuExportNativeScript";
            this.menuExportNativeScript.Size = new System.Drawing.Size(189, 22);
            this.menuExportNativeScript.Text = "Export Native Script...";
            this.menuExportNativeScript.Click += new System.EventHandler(this.menuExportNativeScript_Click);
            // 
            // toolStripSeparator2
            // 
            this.toolStripSeparator2.Name = "toolStripSeparator2";
            this.toolStripSeparator2.Size = new System.Drawing.Size(186, 6);
            // 
            // menuExit
            // 
            this.menuExit.Name = "menuExit";
            this.menuExit.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Alt | System.Windows.Forms.Keys.F4)));
            this.menuExit.Size = new System.Drawing.Size(189, 22);
            this.menuExit.Text = "Exit";
            this.menuExit.Click += new System.EventHandler(this.menuExit_Click);
            // 
            // menuMap
            // 
            this.menuMap.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.menuListObjects,
            this.menuScripts,
            this.menuGroups,
            this.menuPolygons,
            this.menuWaypoints,
            this.toolStripSeparator3,
            this.menuFixExtents,
            this.menuMapGenerator});
            this.menuMap.Name = "menuMap";
            this.menuMap.Size = new System.Drawing.Size(43, 20);
            this.menuMap.Text = "&Map";
            // 
            // menuListObjects
            // 
            this.menuListObjects.Name = "menuListObjects";
            this.menuListObjects.ShortcutKeys = ((System.Windows.Forms.Keys)(((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.Shift) 
            | System.Windows.Forms.Keys.O)));
            this.menuListObjects.Size = new System.Drawing.Size(207, 22);
            this.menuListObjects.Text = "Objects";
            this.menuListObjects.Click += new System.EventHandler(this.menuListObjects_Click);
            // 
            // menuScripts
            // 
            this.menuScripts.Name = "menuScripts";
            this.menuScripts.ShortcutKeys = ((System.Windows.Forms.Keys)(((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.Shift) 
            | System.Windows.Forms.Keys.S)));
            this.menuScripts.Size = new System.Drawing.Size(207, 22);
            this.menuScripts.Text = "Scripts";
            this.menuScripts.Click += new System.EventHandler(this.menuScripts_Click);
            // 
            // menuGroups
            // 
            this.menuGroups.Name = "menuGroups";
            this.menuGroups.ShortcutKeys = ((System.Windows.Forms.Keys)(((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.Shift) 
            | System.Windows.Forms.Keys.G)));
            this.menuGroups.Size = new System.Drawing.Size(207, 22);
            this.menuGroups.Text = "Groups";
            this.menuGroups.Click += new System.EventHandler(this.menuGroups_Click);
            // 
            // menuPolygons
            // 
            this.menuPolygons.Name = "menuPolygons";
            this.menuPolygons.ShortcutKeys = ((System.Windows.Forms.Keys)(((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.Shift) 
            | System.Windows.Forms.Keys.P)));
            this.menuPolygons.Size = new System.Drawing.Size(207, 22);
            this.menuPolygons.Text = "Polygons";
            this.menuPolygons.Click += new System.EventHandler(this.menuPolygons_Click);
            // 
            // menuWaypoints
            // 
            this.menuWaypoints.Name = "menuWaypoints";
            this.menuWaypoints.ShortcutKeys = ((System.Windows.Forms.Keys)(((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.Shift) 
            | System.Windows.Forms.Keys.W)));
            this.menuWaypoints.Size = new System.Drawing.Size(207, 22);
            this.menuWaypoints.Text = "Waypoints";
            this.menuWaypoints.Click += new System.EventHandler(this.menuWaypoints_Click);
            // 
            // toolStripSeparator3
            // 
            this.toolStripSeparator3.Name = "toolStripSeparator3";
            this.toolStripSeparator3.Size = new System.Drawing.Size(204, 6);
            // 
            // menuFixExtents
            // 
            this.menuFixExtents.Name = "menuFixExtents";
            this.menuFixExtents.Size = new System.Drawing.Size(207, 22);
            this.menuFixExtents.Text = "Fix Extents";
            this.menuFixExtents.Click += new System.EventHandler(this.menuFixExtents_Click);
            // 
            // menuMapGenerator
            // 
            this.menuMapGenerator.Name = "menuMapGenerator";
            this.menuMapGenerator.Size = new System.Drawing.Size(207, 22);
            this.menuMapGenerator.Text = "Map Generator...";
            this.menuMapGenerator.Click += new System.EventHandler(this.menuMapGenerator_Click);
            // 
            // menuOptions
            // 
            this.menuOptions.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.menuShowGrid,
            this.menuShowMinimap,
            this.menuVisualPreviewMode,
            this.menuInvertColors,
            this.toolStripSeparator4,
            this.menuSettings});
            this.menuOptions.Name = "menuOptions";
            this.menuOptions.Size = new System.Drawing.Size(61, 20);
            this.menuOptions.Text = "&Options";
            // 
            // menuShowGrid
            // 
            this.menuShowGrid.Checked = true;
            this.menuShowGrid.CheckState = System.Windows.Forms.CheckState.Checked;
            this.menuShowGrid.Name = "menuShowGrid";
            this.menuShowGrid.ShortcutKeys = System.Windows.Forms.Keys.F5;
            this.menuShowGrid.Size = new System.Drawing.Size(223, 22);
            this.menuShowGrid.Text = "Show Grid";
            this.menuShowGrid.Click += new System.EventHandler(this.menuShowGrid_Click);
            // 
            // menuShowMinimap
            // 
            this.menuShowMinimap.Checked = true;
            this.menuShowMinimap.CheckState = System.Windows.Forms.CheckState.Checked;
            this.menuShowMinimap.Name = "menuShowMinimap";
            this.menuShowMinimap.ShortcutKeys = System.Windows.Forms.Keys.F4;
            this.menuShowMinimap.Size = new System.Drawing.Size(223, 22);
            this.menuShowMinimap.Text = "Show Minimap";
            this.menuShowMinimap.Click += new System.EventHandler(this.menuShowMinimap_Click);
            // 
            // menuVisualPreviewMode
            // 
            this.menuVisualPreviewMode.Checked = true;
            this.menuVisualPreviewMode.CheckState = System.Windows.Forms.CheckState.Checked;
            this.menuVisualPreviewMode.Name = "menuVisualPreviewMode";
            this.menuVisualPreviewMode.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.F)));
            this.menuVisualPreviewMode.Size = new System.Drawing.Size(223, 22);
            this.menuVisualPreviewMode.Text = "Visual Preview Mode";
            this.menuVisualPreviewMode.Click += new System.EventHandler(this.menuVisualPreviewMode_Click);
            // 
            // menuInvertColors
            // 
            this.menuInvertColors.Name = "menuInvertColors";
            this.menuInvertColors.Size = new System.Drawing.Size(223, 22);
            this.menuInvertColors.Text = "Invert Colors";
            this.menuInvertColors.Click += new System.EventHandler(this.menuInvertColors_Click);
            // 
            // toolStripSeparator4
            // 
            this.toolStripSeparator4.Name = "toolStripSeparator4";
            this.toolStripSeparator4.Size = new System.Drawing.Size(220, 6);
            // 
            // menuSettings
            // 
            this.menuSettings.Name = "menuSettings";
            this.menuSettings.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.G)));
            this.menuSettings.Size = new System.Drawing.Size(223, 22);
            this.menuSettings.Text = "Settings...";
            this.menuSettings.Click += new System.EventHandler(this.menuSettings_Click);
            // 
            // menuHelp
            // 
            this.menuHelp.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.menuHelpLink1,
            this.menuHelpLink2,
            this.toolStripSeparator5,
            this.menuHelpLink3,
            this.menuHelpLink5,
            this.menuHelpLink4,
            this.toolStripSeparator6,
            this.menuAbout});
            this.menuHelp.Name = "menuHelp";
            this.menuHelp.Size = new System.Drawing.Size(44, 20);
            this.menuHelp.Text = "&Help";
            // 
            // menuHelpLink1
            // 
            this.menuHelpLink1.Name = "menuHelpLink1";
            this.menuHelpLink1.Size = new System.Drawing.Size(180, 22);
            this.menuHelpLink1.Text = "Nox Forum";
            this.menuHelpLink1.Click += new System.EventHandler(this.menuHelpLink1_Click);
            // 
            // menuHelpLink2
            // 
            this.menuHelpLink2.Name = "menuHelpLink2";
            this.menuHelpLink2.Size = new System.Drawing.Size(180, 22);
            this.menuHelpLink2.Text = "Nox Discord";
            this.menuHelpLink2.Click += new System.EventHandler(this.menuHelpLink2_Click);
            // 
            // toolStripSeparator5
            // 
            this.toolStripSeparator5.Name = "toolStripSeparator5";
            this.toolStripSeparator5.Size = new System.Drawing.Size(177, 6);
            // 
            // menuHelpLink3
            // 
            this.menuHelpLink3.Name = "menuHelpLink3";
            this.menuHelpLink3.Size = new System.Drawing.Size(180, 22);
            this.menuHelpLink3.Text = "Game Texts";
            this.menuHelpLink3.Click += new System.EventHandler(this.menuHelpLink3_Click);
            // 
            // menuHelpLink4
            // 
            this.menuHelpLink4.Name = "menuHelpLink4";
            this.menuHelpLink4.Size = new System.Drawing.Size(180, 22);
            this.menuHelpLink4.Text = "Script 3.0 Wiki";
            this.menuHelpLink4.Click += new System.EventHandler(this.menuHelpLink4_Click);
            // 
            // toolStripSeparator6
            // 
            this.toolStripSeparator6.Name = "toolStripSeparator6";
            this.toolStripSeparator6.Size = new System.Drawing.Size(177, 6);
            // 
            // menuAbout
            // 
            this.menuAbout.Name = "menuAbout";
            this.menuAbout.Size = new System.Drawing.Size(180, 22);
            this.menuAbout.Text = "About";
            this.menuAbout.Click += new System.EventHandler(this.menuAbout_Click);
            // 
            // menuShortcuts
            // 
            this.menuShortcuts.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.menuUndo,
            this.menuRedo,
            this.menuPicker,
            this.menuRectangleDraw,
            this.menuLineDraw,
            this.menuRotateSelection45,
            this.menuDrawWalls,
            this.menuDrawObjects,
            this.menuDraw3DExtents,
            this.menuDrawTeleportPaths,
            this.menuDrawWaypoints,
            this.menuColorSpecialWalls});
            this.menuShortcuts.Name = "menuShortcuts";
            this.menuShortcuts.Size = new System.Drawing.Size(69, 20);
            this.menuShortcuts.Text = "Shortcuts";
            this.menuShortcuts.Visible = false;
            // 
            // menuUndo
            // 
            this.menuUndo.Name = "menuUndo";
            this.menuUndo.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.Z)));
            this.menuUndo.Size = new System.Drawing.Size(216, 22);
            this.menuUndo.Text = "Undo";
            this.menuUndo.Click += new System.EventHandler(this.menuUndo_Click);
            // 
            // menuRedo
            // 
            this.menuRedo.Name = "menuRedo";
            this.menuRedo.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.Y)));
            this.menuRedo.Size = new System.Drawing.Size(216, 22);
            this.menuRedo.Text = "Redo";
            this.menuRedo.Click += new System.EventHandler(this.menuRedo_Click);
            // 
            // menuPicker
            // 
            this.menuPicker.Name = "menuPicker";
            this.menuPicker.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.A)));
            this.menuPicker.Size = new System.Drawing.Size(216, 22);
            this.menuPicker.Text = "Picker";
            this.menuPicker.Click += new System.EventHandler(this.menuPicker_Click);
            // 
            // menuRectangleDraw
            // 
            this.menuRectangleDraw.Name = "menuRectangleDraw";
            this.menuRectangleDraw.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.R)));
            this.menuRectangleDraw.Size = new System.Drawing.Size(216, 22);
            this.menuRectangleDraw.Text = "Rectangle Draw";
            this.menuRectangleDraw.Click += new System.EventHandler(this.menuRectangleDraw_Click);
            // 
            // menuLineDraw
            // 
            this.menuLineDraw.Name = "menuLineDraw";
            this.menuLineDraw.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.T)));
            this.menuLineDraw.Size = new System.Drawing.Size(216, 22);
            this.menuLineDraw.Text = "Line Draw";
            this.menuLineDraw.Click += new System.EventHandler(this.menuLineDraw_Click);
            // 
            // menuRotateSelection45
            // 
            this.menuRotateSelection45.Name = "menuRotateSelection45";
            this.menuRotateSelection45.ShortcutKeys = ((System.Windows.Forms.Keys)((System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.D)));
            this.menuRotateSelection45.Size = new System.Drawing.Size(216, 22);
            this.menuRotateSelection45.Text = "Rotate Selection 45";
            this.menuRotateSelection45.Click += new System.EventHandler(this.menuRotateSelection45_Click);
            // 
            // menuDrawWalls
            // 
            this.menuDrawWalls.Name = "menuDrawWalls";
            this.menuDrawWalls.ShortcutKeys = System.Windows.Forms.Keys.F6;
            this.menuDrawWalls.Size = new System.Drawing.Size(216, 22);
            this.menuDrawWalls.Text = "Draw Walls";
            this.menuDrawWalls.Click += new System.EventHandler(this.menuDrawWalls_Click);
            // 
            // menuDrawObjects
            // 
            this.menuDrawObjects.Name = "menuDrawObjects";
            this.menuDrawObjects.ShortcutKeys = System.Windows.Forms.Keys.F7;
            this.menuDrawObjects.Size = new System.Drawing.Size(216, 22);
            this.menuDrawObjects.Text = "Draw Objects";
            this.menuDrawObjects.Click += new System.EventHandler(this.menuDrawObjects_Click);
            // 
            // menuDraw3DExtents
            // 
            this.menuDraw3DExtents.Name = "menuDraw3DExtents";
            this.menuDraw3DExtents.ShortcutKeys = System.Windows.Forms.Keys.F8;
            this.menuDraw3DExtents.Size = new System.Drawing.Size(216, 22);
            this.menuDraw3DExtents.Text = "Draw 3D Extents";
            this.menuDraw3DExtents.Click += new System.EventHandler(this.menuDraw3DExtents_Click);
            // 
            // menuDrawTeleportPaths
            // 
            this.menuDrawTeleportPaths.Name = "menuDrawTeleportPaths";
            this.menuDrawTeleportPaths.ShortcutKeys = System.Windows.Forms.Keys.F9;
            this.menuDrawTeleportPaths.Size = new System.Drawing.Size(216, 22);
            this.menuDrawTeleportPaths.Text = "Draw Teleport Paths";
            this.menuDrawTeleportPaths.Click += new System.EventHandler(this.menuDrawTeleportPaths_Click);
            // 
            // menuDrawWaypoints
            // 
            this.menuDrawWaypoints.Name = "menuDrawWaypoints";
            this.menuDrawWaypoints.ShortcutKeys = System.Windows.Forms.Keys.F10;
            this.menuDrawWaypoints.Size = new System.Drawing.Size(216, 22);
            this.menuDrawWaypoints.Text = "Draw Waypoints";
            this.menuDrawWaypoints.Click += new System.EventHandler(this.menuDrawWaypoints_Click);
            // 
            // menuColorSpecialWalls
            // 
            this.menuColorSpecialWalls.Name = "menuColorSpecialWalls";
            this.menuColorSpecialWalls.ShortcutKeys = System.Windows.Forms.Keys.F11;
            this.menuColorSpecialWalls.Size = new System.Drawing.Size(216, 22);
            this.menuColorSpecialWalls.Text = "Color Special Walls";
            this.menuColorSpecialWalls.Click += new System.EventHandler(this.menuColorSpecialWalls_Click);
            // 
            // menuHelpLink5
            // 
            this.menuHelpLink5.Name = "menuHelpLink5";
            this.menuHelpLink5.Size = new System.Drawing.Size(180, 22);
            this.menuHelpLink5.Text = "Script Wiki";
            this.menuHelpLink5.Click += new System.EventHandler(this.menuHelpLink5_Click);
            // 
            // MainWindow
            // 
            this.AutoScaleBaseSize = new System.Drawing.Size(5, 13);
            this.ClientSize = new System.Drawing.Size(1008, 741);
            this.Controls.Add(this.panelTabs);
            this.Controls.Add(this.mainMenuStrip);
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.KeyPreview = true;
            this.MainMenuStrip = this.mainMenuStrip;
            this.MinimumSize = new System.Drawing.Size(400, 400);
            this.Name = "MainWindow";
            this.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen;
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.MainWindow_FormClosing);
            this.SizeChanged += new System.EventHandler(this.miniViewPanel_Resize);
            this.KeyDown += new System.Windows.Forms.KeyEventHandler(this.MainWindow_KeyDown);
            this.Move += new System.EventHandler(this.miniViewPanel_Resize);
            this.Resize += new System.EventHandler(this.MainWindow_Resize);
            this.mapInfoTab.ResumeLayout(false);
            this.groupMapInfoTab.ResumeLayout(false);
            this.groupMapInfoTab.PerformLayout();
            this.minimapTab.ResumeLayout(false);
            this.MinimapPanel.ResumeLayout(false);
            this.panelInnerMinimap.ResumeLayout(false);
            this.groupMiniMapTab.ResumeLayout(false);
            this.groupMiniMapTab.PerformLayout();
            this.MiniEditPanel.ResumeLayout(false);
            this.MiniEditPanel.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.numBrushSize)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.numMinimapZoom)).EndInit();
            this.largeMap.ResumeLayout(false);
            this.panelTabs.ResumeLayout(false);
            this.mapImageTab.ResumeLayout(false);
            this.mapImageTab.PerformLayout();
            this.groupImgExport.ResumeLayout(false);
            this.groupImgExport.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.trackImgSize)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.numImgPadding)).EndInit();
            this.groupImgEntities.ResumeLayout(false);
            this.groupImgEntities.PerformLayout();
            this.groupImgObjects.ResumeLayout(false);
            this.groupImgObjects.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.picMapImage)).EndInit();
            this.mainMenuStrip.ResumeLayout(false);
            this.mainMenuStrip.PerformLayout();
            this.ResumeLayout(false);
            this.PerformLayout();

        }
        #endregion
    }
}
