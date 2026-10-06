# Dialogue in Westwood's Nox: the style guide

How people talk in Nox's campaign, so the lines of a generated map can stand beside Westwood's and not be told apart.
Measured 2026-10-05 on the campaign's own text (the string table `nox.csf`, keys `Con*`, `War*`, `Wiz*`, `Journal:*`:
1204 distinct strings, 854 of them spoken) with `review/storylab/metrics.py`; quest logic from the 107 campaign maps'
decompiled scripts. Never the quest maps (G_*) or multiplayer. Check a map's story with
`py tests/storylab.py --check mapgen/designs/<map>.py`; the lab that tunes this guide is `review/storylab/`.

## The numbers

Words per line by situation (p10 / median / p90), and how the lines sound (share of lines):

| situation | lines | words | words a sentence | exclaim | ask | address the player | name a person or place |
|---|---|---|---|---|---|---|---|
| quest offer | 108 | 8 / 39 / 73 | 9 | 51% | 26% | 33% | 1.6 a line |
| reminder | 64 | 5 / 12 / 28 | 6 | 59% | 20% | 11% | 0.7 |
| completion (thanks, reward) | 57 | 9 / 24 / 47 | 8 | 82% | 11% | 23% | 0.9 |
| afterwards | 29 | 4 / 9 / 20 | 6 | 38% | 3% | 17% | 0.2 |
| refusal | 14 | 7 / 14 / 28 | 7.5 | 14% | 7% | 14% | 0.4 |
| townsfolk (rumours, barks) | 131 | 5 / 12 / 24 | 7 | 50% | 16% | 6% | 0.7 |
| guards | 48 | 6 / 13 / 27 | 6.5 | 52% | 12% | 6% | 1.1 |
| shopkeepers | 84 | 7 / 12 / 24 | 6 | 49% | 36% | 24% | 0.9 |
| journal | 82 | 5 / 9 / 14 | 8 | 6% | 0% | 0% | 1.4 |
| all dialogue | 854 | 4 / 13 / 41 | 7 | 56% | 17% | 14% | 0.8 |

- **Two lines in three exclaim or ask.** Semicolons: 3 in 854 lines. Colons mid-line: almost none. Westwood joins
  and breaks clauses with ` -- ` and trails off with `...` (ASCII, never an em dash or a typographic ellipsis).
- **One word in nine** of a Westwood line (not counting names) is a word the rest of the campaign never uses. Its
  vocabulary is small and everyday.
- **Lines per person:** 64% of the campaign's speakers say one line; p90 is 4. A quest giver has 4 to 6 (offer,
  refusal, reminder, completion, afterwards); a main-quest giver up to 10 across a chapter.
- **A long speech is split into pages** by a blank line (`"\n\n"`): offers 1-3 pages (p90 3), completions 1-2, all the
  rest one.

## The voice, in twelve rules

1. **Plain and loud.** People say what they feel, at once, with `!`: "My boots! I never thought I'd see them again!"
   "It's a disaster!" "Thank goodness, you saved him!" Understatement, irony, subtext and literary restraint mark
   another writer. Our maps' house style ("Forty years I worked beside him. He'd hand me the stones before I
   asked.") is good prose and not Nox.
2. **Short sentences, one idea each:** 7 words at the median, rarely over 15. No semicolons, no colons inside a
   line; use ` -- ` or start a new sentence.
3. **Feelings named, not shown:** "I'm inconsolable." "I fear the worst." "I'm eternally grateful, mate." "These
   cursed arachnids are worse than the pox!"
4. **Address the player** as a stranger would, in one line in seven (a third of the offers): *lad*, *kind sir*,
   *brave Adventurer*, *kind stranger*, *Wanderer*, *friend*, *mate*, *my son*, *young sir*. **Never name the
   player's class**: our maps are played by Warriors, Wizards and Conjurers alike. Westwood's own class-free chapter
   (Brin, the same text in all three campaigns) speaks exactly so.
5. **Everyday words.** Potions, not philtres; a garden, not a herbarium; a cart, not a wain. Name a thing by what it
   is. A word a farmer would not say needs a reason.
6. **The genre's stock phrases are Nox's texture**, used straight, not winked at: "a token of my appreciation", "I
   will offer a worthy reward", "Please, help me!", "Hurry!", "Thank goodness!", "May all that is great bless you!",
   "Good luck!", "Thanks again, brave Adventurer!". Vary them across a map; do not avoid them.
7. **Capitalise creature kinds, peoples and titles** as Westwood does: the Ogres, the Urchins, the Undead, the
   Necromancer, the Mayor, the Captain, the Foreman.
8. **Say where, by compass and landmark:** "in my house northwest of here", "east out of town, across the bridge",
   "the Ogre village in the northeast", "Go into the cemetery located East of here". A quest line that sends the
   player somewhere says where it is.
9. **Humour is broad, and in a corner:** the frog ("You know, I've been thinking... being a frog isn't half bad!"),
   the con man's bow ("The previous owner only used it on weekends."), the barkeeper ("The ale's fresher'n a monkey's
   butt!"), the archery judge ("Maybe we should get bigger barrels for you."), a shopkeeper who takes back his boast
   ("Well... Maybe not the finest exactly... But damn good nonetheless!"). One or two comic lines a town, from minor
   people; never in the journal, rarely in a quest giver's plea.
10. **Spoken sounds are written out:** "Heh, heh, heh...", "Hmmm.", "Psst...over here", "Ahhhh!", "Gahhhhhh! No!
    Don't kill me!", "Arf, Arf! Grrrrrrrrrr.", "*RIBBIT*", "Hiccup!". Townsfolk and odd characters use them; givers
    sometimes.
11. **Dialect is light and rare:** "C'mon in, lad!", "Name yer poison! What can I get fer you?", "What 'dat noise?"
    (Ogres), "mate" (a bridge guard). One or two characters a map, not everyone.
12. **Repeat freely.** Westwood reuses a line across people ("Thanks again, brave Adventurer!" from three villagers)
    and across maps. A town's after-lines may say the same thing in the same words.

## The situations

### The quest offer (the giver's first words)

The trouble, who caused it and where, the ask, and the reward, in that order; often ending in a yes/no question
(Westwood's YESNO dialog, 56 uses, one or two a map). 2-4 sentences a page, 1-3 pages.

> Greetings, brave Adventurer! Please, help me, a horrific fate has befallen my wife! / Not long ago, a raving
> demoness led the Ogres through here. She cast an evil spell, turning my poor wife into a wolf! I could reverse this
> curse if I only had my magic staff, but I left it in my house northwest of here. I'm afraid if I leave to go
> retrieve it, my wife will run off! / Would you help me by fetching my staff for me, kind sir? I will offer a worthy
> reward for its timely return. (War05A, the farmer)

> Sorry, mate, the bridge is washed out! Only way across the stream is there, through the Urchin den. But, if you
> choose that route, mate, keep your guard up! The Urchins stole my best boots when I was bathing! / If you bring 'em
> back, mate, I'll teach you a damn fine spell. (Con02a, the bridge guard)

> Gahhhhhh! No! Don't kill me! / Oh. A young man?! I can't see well at all. But I know you're not one of those
> infernal bandits who stole my spectacles! I'm almost blind without them. / If you could get them back, you'd save my
> life and I'd be eternally grateful. (Con03A, the hermit)

### The refusal (the player said no)

One short sulk or a sigh; the giver asks again next time ("Hello, again. Will you change your mind, be our savior
and lead us to the surface?").

> Fine then, don't return my magical staff! (War05A) -- I'm sorry to hear that. I hope you reconsider your decision
> soon, for I fear the Ogres are getting hungry. (War05C) -- Too bad, I don't think you'll have much luck finding
> other sponsors. (War01A)

### The reminder (while the quest is open)

One or two short sentences: the ask again, with urgency; sometimes the way again.

> What are you waiting for? I need my magical staff! -- Please hurry, kind sir! My father will be home soon! -- Have
> you recovered my spectacles?! Oh.... Well, the rogues who took them have a hideout in the woods nearby. -- Hurry and
> find the Amulet! Please go swiftly!

### The completion (it is done)

Delight first, then thanks, then the reward put in the player's hands ("take this", "here is", "as promised", "a
token of my appreciation"); a big one may point to what comes next.

> My boots! I never thought I'd see them again! I'm eternally grateful, mate. Here's the Spell, as promised. (Con02a)

> My spectacles! You brought them back! May all that is great bless you! And please, take this scroll. It contains
> all I have learned about bats. It would be invaluable to any conjurer. (Con03A)

> Oh, thank you so much! Please accept this as a token of my appreciation! (War05A)

### Afterwards

A few words, the same each time: "Thanks again, brave Adventurer!", "Thanks again, kind stranger!", "My heartfelt
thanks again for rescuing my sister!", "A thousand thanks for your kindness!".

### Townsfolk: rumours and barks

One or two sentences. A rumour names a person or a place and carries the hook of a quest; a bark is flavour, a
brush-off or gossip with a sting. A town mixes both, and they change after the quest ("Nice job with the spiders,
Conjurer! I hear the Mayor is very impressed!").

> I saw a huge spider crawl towards the mayor's house! I hope he's alright -- he's deathly afraid of spiders! -- Most
> of us stay away from the river. Nearby urchins will steal the clothes right off you back! -- Bandits have been
> preying on the trade routes between Galava and Ix. Be careful if you plan on traveling. -- I'm late for an
> appointment, sorry. -- I've been told not to talk to strangers. -- Have a drink, stranger. The ogres took the
> women, but at least they left the cider.

### Guards

Rules, warnings and directions, in short imperatives; a guard is curt and proud of his post.

> Sorry. You can't leave without Mayor Theogrin's permission. It's meant for your own good. The wilds hold far too
> many perils for the common man. -- Move on! -- The Mayor has given permission for your departure. You may pass. --
> Welcome to Dün Mir! We keep a tidy city. No street brawls, foul language, or spitting is allowed. And don't even think
> about wizardry. Enjoy your stay. -- Oh, I forgot to mention, no loitering. Now move on.

### Shopkeepers

The shop's name or wares and a pitch, often with a wink at the price or the times.

> This is Kincaid's. I can sell you armor, but be quick about it. -- Welcome to the Griffon's Nest. My inn may not be
> as fancy as Maximillian's, but I guarantee you a peaceful rest. -- Welcome, Wanderer! We carry the finest wares in
> all of Nox! -- Ah, stranger! Let's get to know each other! Buy something! -- Trouble's brewing, lad. Better stock up
> while you can!

### Captives and followers (a rescue)

Found: a cry, then the plea in a sentence ("Thank you for finding me. Please take me back to the elevator.").
Following: one line, urgent ("Hurry! Lead me to safety!", "Let's hurry, lad! Time waits for no man!").

### The journal

An order, one sentence, 5-14 words (median 9): the goal and where. 30 of Westwood's 82 entries send the player
somewhere or to someone (Find, Go, Locate, Meet, Speak, Return), 18 fetch (Retrieve, Recover, Bring), 13 fight or
clear (Defeat, Charm, Survive, Chase), 11 rescue or escort.

> Retrieve Matilda's cloak from an Ogre near the docks of Brin. -- Find the boots stolen from the bridge guard by the
> Urchins and return them to him. -- Rescue Ingrid's sister from the Ogre dungeons. -- Go to the mines and locate the
> mine foreman. -- Charm and banish the spiders in the Mayor's home.

- **Never the first person, never narration** ("I cleared the imps...", "The wards went dark three nights ago..."):
  Westwood's journal is a list of orders.
- **Done:** Westwood greys the same entry (JournalEdit to COMPLETED, "COMPLETED: Retrieve Matilda's cloak..."). OpenNox
  alpha13 lacks JournalEdit, so write a COMPLETED entry with the objective's own words (`q.done(text)` in
  `kit/quests.py`).
- **Information** goes in a `NOTE:` entry: "NOTE: According to a pair of bridge guards, a large band of Ogres just
  marauded through this area -- and laid waste to the Village of Brin!". Hints are their own type (`HINT`), short and
  practical ("Eating food will restore health.").

### Signs and the screen

Signs: 2-7 words. "Residence of Thavius", "Path to Grok Torr -- Travelers beware!", "Humans keep out!", "Cemetery
closed until further notice. Curse Hecubah!". The screen's narration on arrival: one plain sentence ("The air is
fresher out here and the sun is bright.", "This cave is dank and smells of Ogre...").

## Checklist for a map's story

- [ ] Every line's length in its situation's range (the table above); offers paged by blank lines.
- [ ] Two lines in three exclaim or ask; no semicolons; `--` and `...`, never `—` or `…`.
- [ ] Offers: trouble, who, where (compass or landmark), the ask, the reward; a yes/no question for side quests.
- [ ] Each giver: offer, refusal (if asked), reminder, completion with a handover, an afterwards line.
- [ ] Journal entries: orders, 5-14 words, naming the goal and place; done entries with the same words.
- [ ] The player addressed as lad / stranger / kind sir / Adventurer now and then; never by class.
- [ ] Every person, place and thing named is on the map (`--check` flags names used once).
- [ ] A comic line or two, from minor people.
- [ ] `py tests/storylab.py --check mapgen/designs/<map>.py` at 8 or more, no line below 6.
