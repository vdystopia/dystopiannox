# Building an act of The Hollow Choir (for the agents building acts)

You build one or two acts of a ten-act campaign. Several builders work at the same time on this PC, each on its own
acts. The coordinating session installs, server-tests, voices and commits; you build and check.

## Read first
1. `campaign/hollowchoir/BIBLE.md`: the story. Your acts must fit it. Where it is silent, invent within it.
2. `skills/nox-story-map/SKILL.md`: the recipe for a story map. Follow it step by step. Its templates:
   `starwell.py`, `ambermere.py`, `harrowby.py` (towns), `greywatch.py` (castle), `deepvault.py` (cave town),
   `emberhollow.py` (lava), `mirefen.py` (swamp), `rimehold.py` (ice town; old), `ironcrag.py` (transporters),
   `tnorth.py` (a small linking map).
3. `mapgen/kit/campaign.py`: the acts (`ACTS`, map names, design file names), the tokens (`TOKENS`, `token()`,
   `has()`), the recurring cast (`CAST`, `cast_person()`, `voice()`), the named foes (`FOES`), and `exit_next()`.
4. `mods/MODLAB.md` "The API": the new weapons W1-W6 and monsters M1-M5 (`kit/mods.py Mods`). In a story map:
   `mods = Mods(m, sm.pop)` (one Population for the whole map), place what the bible gives your act, and last of all
   `mods.attach(sm.B)` before `m.scripts.update(...)`. Since 2026-10-09 every script shares a creature's events
   (`kit/behaviours/events.go`), so a new monster can also be a quest target (`q.on_death`) or a sentry.
5. `PROCESS.md` and `review/FEEDBACK.md`: the user's rules. They are strict about rooms, exteriors, camps and NPC
   movement. Read the feedback: every item there was a real complaint.

## Your act's design
- File: `mapgen/designs/<design>.py` (the `design` name in `ACTS`), map name from `ACTS` (at most 9 characters).
- Size: bigger than Westwood's (the user's standing rule) but at most Thornwick's size; a linking act may be smaller.
- The exit to the next act: `exit_next(sm, area, n)` behind the act's main-quest gate. The last act has no exit:
  it ends with the closing scene.
- **Continuity.** Give the tokens the bible says your act gives (`A.give(token("NAME"))`; a counted one once per
  find), and read the tokens it says your act reads (`when=has("NAME")`). Every token-reading branch must also work
  without the token: a player who loads your act on its own with an empty pack must still be able to finish it. Say
  in the dialogue what the item is in the story. Never give a token a player can get twice by accident.
- **Recurring cast:** `cast_person(sm, "Ilsa", x, y, face=...)` and `q.talker("Ilsa", [...], voice=voice("Ilsa"))`.
  Their body and voice must be the same in every act.
- **New resources:** the monsters and weapons the bible puts in your act, as the Choir's champions, bosses and
  rewards. Power weapons are earned or found, never laid out as a free armoury. A boss with a quest trigger:
  `mods.monster(...)` named, then `q.on_death(name, [...])`.
- Dialogue: written from Westwood frames (`py tests/storylab.py frames --seed <MapName>`), checked with
  `py tests/storylab.py --check mapgen/designs/<design>.py` (aim 8+, Originality must pass).

## Building and checking
- Build with voices off: `set NOX_NOVOICE=1` (PowerShell: `$env:NOX_NOVOICE = "1"`; Bash: `NOX_NOVOICE=1 py ...`).
  The coordinator voices every act at the end on the GPU, one at a time.
- One build at a time (yours); other builders share the CPU.
- The QA gate: `py tests/qa.py <design> --no-render` while fixing, then once without `--no-render`. Its voice step
  fails without voices: that is expected; everything else must PASS (0 checker errors; warnings accepted only with a
  reason in `QA_ACCEPT`). Look at the pictures it renders (rooms, story places, routes) and fix what looks wrong.
- Do **not** install maps, start the game or the server, or commit. Do **not** edit shared kit files
  (`mapgen/kit/*.py`, `mapgen/kit/behaviours/*.go`, `validate/*`, `mapgen/nox.py`) without need: other builders use
  them at the same time. If the kit lacks something, build it in your design or in a new file
  `mapgen/kit/hc_<topic>.py`, and say in your report what you would change in the shared kit.

## Report (short)
For each act: the design file and map name; the story as built (main quest, side quests, choices); the tokens given
and read, and what each changes; where the new monsters and weapons are; the QA gate summary (and accepted warnings
with reasons); the story-lab score; anything unfinished or uncertain; proposed shared-kit changes.
