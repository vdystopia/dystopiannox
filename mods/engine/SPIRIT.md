# Spirit class: an engine mod for OpenNox

The request: *"create a new class that has 'Spirit' instead of mana and make the Spirit bar cyan instead of mana blue"*.

What exists now: a modified OpenNox engine, `opennox-spirit-hd.exe`. In it, the Conjurer's place is taken by a new class,
the **Mystic**. The Mystic's mana is called **Spirit**, it is drawn **cyan**, and it fills up by different rules.
The normal game (`opennox-hd.exe`) is unchanged and still works as before.

| File | What it is |
|---|---|
| `C:\GOG Games\Nox\opennox-spirit-hd.exe` | the modded game (HD client), built from OpenNox **v1.9.0-alpha13** plus the project's sight-row crash fix (`engine/opennox/sight-row-overflow.patch`, which the installed `opennox-hd.exe` "alpha13-sightfix" also has) plus `spirit.patch`; reports `v1.9.0-alpha13-sightfix-spirit` |
| `C:\GOG Games\Nox\opennox-spirit-server.exe` | the same mod as a dedicated server (only needed to host a multiplayer server with no game window) |
| `C:\GOG Games\Nox\Nox Spirit Test.ps1` and `Nox Spirit Test.lnk` | launcher (works like `Nox Map Test`) |
| `mods/engine/spirit.patch` | the source change (`git diff` against the v1.9.0-alpha13 tag) |
| `mods/engine/build-spirit.sh` | the build script (Git Bash) |
| `mods/engine/spiritqa.go` | a test map script that measures the Spirit rules |
| `review/out/qa/spirit/` | screenshots and logs from the tests |

---

## 1. What the Mystic is

Nox has exactly three classes, and the number three is built into everything: the save files, the network messages,
the stats tables in `gamedata.bin`, the spell lists, the armour and weapon rules, the character art and the menus
(see section 6). A real fourth slot would break saves and multiplayer and take weeks of work.

So the Mystic **reuses the Conjurer's slot**. It has the Conjurer's body, spells, summons, armour and weapons. What
changes is how the class is named and how its magic works:

| | Conjurer (normal game) | Mystic (Spirit build) |
|---|---|---|
| Name everywhere (new character screen, save list, level titles such as "Arch-Mystic", scoreboard "MYS") | Conjurer | **Mystic** |
| Magic pool | Mana, blue tube | **Spirit, cyan tube** (and cyan bubbles, and a cyan mini bar beside the character) |
| Texts | "Your Mana", "Mana:", "Mana cost: High", "not enough mana" | "Your **Spirit**", "**Spirit**:", "**Spirit** cost: High", "not enough **spirit**" |
| Refills over time | normal rate | **3 times slower** |
| Mana crystals / obelisks | refill mana | **do nothing** (the Mystic can't take Spirit from crystals) |
| Hitting enemies | nothing | **half the damage of every physical hit becomes Spirit** (staff, bow and arrows, fists; enemy creatures and players; spells don't count) |
| Blue (mana) potions | restore mana | restore Spirit (renamed "Potion of Restore Spirit") |

The idea: the Mystic is a Conjurer who must fight up close to keep their magic going, instead of standing by a crystal.

Warrior and Wizard are unchanged in this build, except that the general texts listed above ("Mana cost", "not enough
mana") say "Spirit" for everyone, because Nox shares one text table for all classes.

Choices that can be changed at launch (see section 3): `-spirit wizard` makes the **Wizard** the Spirit class instead,
`-spirit off` turns the mod off, and `-spirit-name Shaman` gives the class another name. The numbers (3 times slower,
half the damage) are in `src/spirit/spirit.go` (`PassiveSlowdown`, `HitPercent`).

---

## 2. How to play it, step by step

**The quick way (straight into a test map):**

1. Open the folder `C:\GOG Games\Nox` in File Explorer.
2. Open a PowerShell window in that folder: click the address bar at the top of File Explorer, type `powershell`,
   press Enter. In the blue window that opens, type this and press Enter:

   ```powershell
   powershell -ExecutionPolicy Bypass -File ".\Nox Spirit Test.ps1" -Map estate
   ```

   (`estate` can be any map folder name in `C:\GOG Games\Nox\maps`.) The game opens in a window, already in that map,
   playing a Mystic, in a private game that nobody else can see or join. To compare with a normal class in the same
   build, add `-Class wizard` or `-Class warrior`.
3. Look at the bottom right: the right-hand tube is cyan. Hover the mouse over it: it says "Your Spirit".
4. Close the game window when done. The launcher puts your normal settings file (`nox.cfg`) back by itself.

**The normal way (a Mystic character of your own, for the solo quest or multiplayer):**

1. Double-click `Nox Spirit Test.lnk` in `C:\GOG Games\Nox` (or run `Nox Spirit Test.ps1` with no options).
2. In the menu choose **Solo** (or Multiplayer), then **New** to make a character.
3. The class that used to be "Conjurer" is now named **Mystic** in the texts (the class picture is still the
   Conjurer's; see section 4). Pick it, name your character, and play.
4. Characters made this way are saved as ordinary Conjurers (the save format has no room for a fourth class). Open the
   same save in the normal `opennox-hd.exe` and it plays as a normal Conjurer; open it in `opennox-spirit-hd.exe`
   and it plays as a Mystic.

You can also just double-click `opennox-spirit-hd.exe`: any exe with "spirit" in its name turns the mod on by itself.
It then runs full-screen with your usual settings (the launcher instead uses the 1920x1080 test window).

---

## 3. Command-line options added by the mod

| Option | Meaning |
|---|---|
| `-spirit conjurer` / `-spirit wizard` / `-spirit off` | which class becomes the Spirit class. Default: `conjurer` when the exe's name contains "spirit", otherwise `off` (so the patch is harmless in a normal-named build) |
| `-spirit-name NAME` | display name of the Spirit class (default `Mystic`) |
| `-autoclass conjurer\|wizard\|warrior` | test helper: with `-autosrv -autoexec "load MAP"`, start the map **playing** that class (normally the host of an `-autosrv` game only watches, as an observer) |

---

## 4. Verified vs. not tested

**Verified** (on this PC, 2026-10-09, with the final build):

* The toolchain builds an unmodified `opennox-hd.exe` from the v1.9.0-alpha13 tag (60.6 MB; it needs the same DLLs as
  the installed one: `SDL2.dll`, `OpenAL32.dll`, `OPENGL32.DLL`, `WS2_32.dll`, `KERNEL32.dll`, `msvcrt.dll`).
* The Spirit build starts, reports `v1.9.0-alpha13-sightfix-spirit (57827e6)`, loads maps as client and as
  dedicated server, with the game folder's existing DLLs.
* **Cyan bar**: screenshots `review/out/qa/spirit/tubes_mana_vs_spirit.png` (left: same build with `-spirit off`,
  blue; right: Mystic, cyan, with cyan bubbles), `spirit_on_full.png`, `spirit_off_full.png`. Pixel check of the tube:
  RGB(78,255,255) with Spirit vs RGB(42,27,173) without.
* **Texts** (from the log, `review/out/qa/spirit/strings_check.txt`): `SelChar.c:Conjurer = "Mystic"`,
  `experience:Conjurer9 = "Arch-Mystic"`, `guirank.c:Conjurer = "MYS"`, `guimeter.c:ToolTipMana = "Your Spirit"`,
  `GuiInv.c:StatsMana = "Spirit:"`, `guibook.c:ManaCostHigh = "Spirit cost: High"`; 39 class-name and 16 mana texts changed.
* **Spirit rules**, measured with `spiritqa.go` on a copy of the Estate map (`qa_spirit_on.txt` / `qa_spirit_off.txt`),
  Conjurer with 125 max:

  | Test | Spirit build | Same build, `-spirit off` |
  |---|---|---|
  | refill over 30 s from empty | 0 -> 4 | 0 -> 12 (3 times more) |
  | five blade hits of 10 on a troll | 0 -> 5 -> 11 -> 16 -> 21 -> 26 | 0 -> 2 (only the time refill) |
  | one fire hit of 10 | +0 | +0 |
  | 6 s beside a mana obelisk, from empty | 0 -> 1 (time refill only) | 0 -> 52 |

* The launcher starts the game with the right options and restores `nox.cfg` (checked by file hash).

**Not tested** (needs a person at the keyboard; the test tools could not click inside the game window):

* The new-character screen itself (the text is checked in the string table, not seen on screen). The class picture
  and the class button art are pictures, not text, so they still show the Conjurer.
* A real fight with a staff or bow (the test hit the troll through the script, which goes through the same damage code).
* Saving and loading a Mystic in the solo quest; multiplayer with other players.
* `opennox-spirit-server.exe` with players connected (it was only started and loaded a map).

**Known limits:**

* Only the HD client was built. If you want the 640x480 `opennox.exe` variant, build target `client` too.
* The mod is chosen by the program, not stored in the save. A Mystic save opened in the normal exe is a Conjurer.
* In multiplayer, every computer should run the Spirit build: the server decides the Spirit rules, each player's own
  game draws the bar and the texts.
* The mod's general texts ("Spirit cost", "not enough spirit") also show for a Wizard in the same game.

---

## 5. Build recipe (exact)

All tools are portable (unzipped into a folder, nothing installed on Windows). Commands are for **Git Bash**.

| Tool | Version | Download |
|---|---|---|
| OpenNox source | tag `v1.9.0-alpha13`, commit 57827e6 (2024-01-21) | `git clone --depth 1 --branch v1.9.0-alpha13 https://github.com/noxworld-dev/opennox.git` |
| Go | 1.23.4 windows/amd64 (any Go 1.21 or newer works; it cross-compiles to 32-bit) | https://go.dev/dl/go1.23.4.windows-amd64.zip |
| C compiler (32-bit MinGW-w64, WinLibs) | GCC 13.2.0, i686, posix threads, dwarf exceptions, msvcrt, r5 | https://github.com/brechtsanders/winlibs_mingw/releases/download/13.2.0posix-17.0.6-11.0.1-msvcrt-r5/winlibs-i686-posix-dwarf-gcc-13.2.0-mingw-w64msvcrt-11.0.1-r5.zip |
| SDL2 headers + import library | 2.32.10 (MinGW) | https://github.com/libsdl-org/SDL/releases/download/release-2.32.10/SDL2-devel-2.32.10-mingw.zip |
| OpenAL headers + import library | openal-soft 1.25.2 | https://github.com/kcat/openal-soft/releases/download/1.25.2/openal-soft-1.25.2-bin.zip |

Why GCC 13 and not the newest (16): OpenNox's C code is old, decompiled C; newer GCC versions turn more of its
warnings into errors. GCC 13 is what the official builds used in 2024.

Steps:

```bash
# 1. get the source and apply the mod
git clone --depth 1 --branch v1.9.0-alpha13 https://github.com/noxworld-dev/opennox.git opennox
cd opennox
git apply "/c/GOG Games/Nox/dystopiannox/engine/opennox/sight-row-overflow.patch"   # crash fix the installed exe has
git apply "/c/GOG Games/Nox/dystopiannox/mods/engine/spirit.patch"

# 2. say where the unzipped tools are (forward slashes; SDL2/OpenAL paths must not contain spaces,
#    use the 8.3 short name such as C:/Users/DYSTOP~1/... if needed)
export GO_DIR=/c/tools/go/bin
export MINGW_DIR=/c/tools/mingw32            # the "mingw32" folder inside the WinLibs zip
export SDL2_DIR=C:/tools/SDL2-2.32.10
export OPENAL_DIR=C:/tools/openal-soft-1.25.2-bin

# 3. build (first build about 5 minutes: it compiles all the C code; later builds take seconds)
NOX_VERSION=v1.9.0-alpha13-sightfix-spirit NAME_HD=opennox-spirit-hd NAME_SRV=opennox-spirit-server \
  bash "/c/GOG Games/Nox/dystopiannox/mods/engine/build-spirit.sh" "$PWD" "$PWD/build" client-hd server

# 4. copy build/opennox-spirit-hd.exe (and the server) into C:\GOG Games\Nox. Never overwrite opennox*.exe.
```

What the script does (the same as the upstream tool `go run ./internal/noxbuild`, which fails when the folder path has
a space in it): `GOOS=windows GOARCH=386 CGO_ENABLED=1 CC=gcc`,
`CGO_CFLAGS_ALLOW='(-fshort-wchar)|(-fno-strict-aliasing)|(-fno-strict-overflow)'`, include/lib paths for SDL2 and
OpenAL, then `go build -tags highres,guiapp -ldflags "-X ...version=v1.9.0-alpha13 -X ...commit=57827e6 -H windowsgui"
-trimpath ./cmd/opennox` (server: tags `server`, no `-H windowsgui`). Build tags: `highres` = the HD client,
`guiapp` = no console window, `server` = dedicated server.

The other OpenNox copy found on this PC (`...\2ef10e66-...\scratchpad\opennox`) is a one-commit snapshot of the `dev`
branch from 2024-11-23 (10 months newer than alpha13, Go 1.22). It was not used, so that the modded exe matches the
installed game and maps.

---

## 6. How the patch works (for whoever changes it next)

| Where | Change |
|---|---|
| `src/spirit/spirit.go` (new) | the settings: which class, its name, the two numbers, `IsClass`, `HitGain` |
| `src/main.go` | the options `-spirit`, `-spirit-name`, `-autoclass`; turns the mod on; rewrites the texts after `nox.csf(.json)` is loaded |
| `src/spirit_strings.go` (new) | the text changes. OpenNox's string library has no way to edit one text, so the whole table is written to a temporary JSON file, edited, and read back |
| `src/object_update.go` (`sub_4F9ED0`, the player's per-frame refill) | Spirit refills 3x slower |
| `src/legacy/GAME3_2.c` (`nox_xxx_damageDefaultProc_4E0B30`, the damage handler for creatures and players) | after the final damage is known, calls `nox_spirit_onPhysicalHit` |
| `src/legacy/spirit.go` (new) | `nox_spirit_onPhysicalHit`: if the attacker is a Mystic, the damage is blade/crush/impale/claw, not from a wand, and the target is a creature or player, add half the damage as Spirit; also `nox_spirit_unitIsSpirit`, `nox_spirit_isClass` for the C code |
| `src/legacy/GAME4_3.c` (`nox_xxx_updateObelisk_53C580`) | obelisks skip Mystics (wands still recharge) |
| `src/legacy/GAME2_1.c` (`nox_xxx_guiHealthManaColorInit_470B00`) | tube and mini-bar colour: cyan RGB(0,255,255) / dark RGB(0,100,100) when the local player's class is the Spirit class |
| `src/legacy/client__gui__guimeter.c` (`nox_xxx_guiHealthManaTubeDraw_471D10`) | bubble colour cyan |
| `src/game.go` | with `-autoclass`, the host plays instead of observing |

The mana tube is not a picture: the engine fills a rectangle with a colour (`nox_client_drawRectFilledOpaque_49CE30`)
inside the glass-tube picture `HealthManaTubes`, so changing the colour is enough.

---

## 7. What a full, separate 4th class would still need

If the Mystic should one day be its own class (its own slot next to the other three, its own save, its own spells),
this is the work, roughly in order of size:

1. **Class number 3** in the player data (`playerInfo` byte at +2251, Go `player.Class`), the save format
   (`.plr` files, `Player_class`), and the network messages that send the class. Old saves and other players' games
   (normal OpenNox) would not understand it, so multiplayer would need everyone on the modded build.
2. **117 places in the C code** that read the class byte and 34 in the Go code that test `player.Warrior/Wizard/Conjurer`
   (e.g. `if class == 2`). Each must decide what class 3 does.
3. **Stats tables**: `gamedata.bin` has `WarriorMaxHealth`, `ConjurerMaxMana`, level-up tables, speed and strength
   per class; `server/player.go` builds the class stats from them. A 4th set of entries and code to read them.
4. **Spells and abilities**: which spells the class can learn and cast (spell flags per class in the spell
   definitions), spell books (`ConjurerSpellBook`), the spell-book and quick-bar GUI (`guispell.c`, `guibook.c` test
   class 1 and 2), the summon/charm rules (Conjurer-only today).
5. **Items**: `nox_xxx_playerClassCanUseItem_57B3D0` and the modifier file (`modifier.bin`, class bit lists
   "Warrior Wizard Conjurer") decide who can wear and wield what.
6. **Menus and art**: the new-character screen (`SelClass` window and its three class buttons and pictures), the
   save list icons, the scoreboard, the Westwood character art and the starting outfit.
7. **The solo quest**: each class has its own chapter maps and scripts (War/Wiz/Con maps). A 4th class needs a
   quest route (it could reuse the Conjurer chapters).

The patch here is written so that this is easier later: everything asks `spirit.IsClass(class)` rather than
"is it the Conjurer", so moving it to a real class number is a one-line change once the slot exists.
