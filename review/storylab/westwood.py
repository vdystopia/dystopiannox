"""Westwood's campaign text, read from the game's string table and sorted by situation.

The lines of the three campaigns (Con/War/Wiz: keys "Con02a:MayorGreeting", "War07A.scr:MorganTalk01") and the
journal ("Journal:BanishSpiders") are read from nox.csf with mapgen/strings.py read_csf (read only: nothing is
written to the game's folder). Never the quest maps (G_*) or multiplayer.

Each line gets a situation from its key (the speaker and the moment are in Westwood's key names: FarmerGreeting,
FarmerWaiting, FarmerReturned, FarmerIdle, FarmerHuffy):

    offer      a giver's first words: the trouble and the ask (Greeting, Intro, Quest, Offer, Pitch, Plea)
    reminder   the giver while the quest is open (Waiting, Prod, Pre, Impatient)
    completion the giver when it is done: thanks and the reward (Returned, Reward, Post, Thanks, Happy)
    after      the giver afterwards (Idle, Post2, End)
    refusal    a no, or not enough gold (Huffy, Sad, TurnDown, Poor, NotEnoughGold)
    townsfolk  passers-by: rumours and barks (Townsman, Maiden, Women, Rumor, RandomSay, T1Pre)
    guard      guards, gatekeepers, wardens, jailers
    shop       shopkeepers, barkeepers, pedlars
    bump       a word when bumped into (Bump, Civvy)
    foe        villains and monsters taunting (Hecubah, Necro, Ogre)
    journal    journal entries (imperative objectives); hint: the journal's hints
    sign       signs; narration: what the screen says (BeginMission); system: game notices
    talk       anything else said

    py review/storylab/westwood.py            the counts by situation and a few lines of each
"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "mapgen"))
CSF = r"C:\GOG Games\Nox\nox.csf"

CAMPAIGN = re.compile(r"^(Con|War|Wiz)\d", re.I)

# key-name patterns, tried in order (the part after "Map:"); the first that matches wins
_SITUATIONS = [
    ("system", r"ObjectiveComplete|EndOfMission|ObjectiveFailed|^Secret$|NewQuest|JournalUpdated|GainedItem|^Hint$|"
               r"PlayerDeath|CityGates|Unlocked|Opened|^Found|^Rescued\d|Added|Tada|TheEnd|^Saved|MaidenDeath|"
               r"NewJournalEntry|GotKey|GotItems|TaskComplete|NewTask|SentryDisabled|^Gained|Defeat[A-Z]|Die$|"
               r"EstimatedGoodies|^Special|SecretPassage|FirstGate|SecondGate|DoorsUnlocked|StoneBlocks|DenyDungeon|"
               r"Contest\d|ScoreKeeper(?!Thanks)|OfficialSEG"),
    ("narration", r"BeginMission|TimePass|Exitmessage|Painting|Mirror"),
    ("sign", r"Sign|^TownOfIx$|^HomeOfTheMayor$|^ItemShop$|^MagicShop$|^Tavern$|^GearRoom$|^Orchard$|^Cemetary$|"
             r"^Gauntlet$|Elevator$|^LightSwitch$|^DunMir$|^IxCemetary$|^Airship$|^Mana$|^BookShop$|Street$|"
             r"^Maximillian$|^WizardShop$|^ArmorShop$|^Lucky$|^Unknown$|^Tragedy$|^Eric$|^Bryan$|^Jason$|^WaterBarrel$|"
             r"^ButtonSign$"),
    ("foe", r"Hecubah|Hec[A-Z]|Necro|Ogre|Dryad|Demon|Bully|MobYell|Recognize|Listen|BigOgre|RogueLeader|"
            r"JumpedByRogues|BanditAmbush|^Guard\d$|^King\d|SetpieceGuard|GraveRobber|MiscWizard|NecroSpiders|"
            r"^Wizard\d|^Wizaard|^Horrendous\d|ChamberMan|TeacherTalk01$|BirdMan|TrapWiz|TempWizard|ExplodingGuy|"
            r"Archivist(Surprise|Snob|Wimp)|^Women[123]$|WardenTalk04$|SpiderMage|HorrendousVsHec|ChallengingHec|"
            r"TauntingHec|^Guard[12]$"),
    ("bump", r"Bump|^RandomBump$|CivvyTalk"),
    ("refusal", r"Huffy|Sad$|TurnMaxDown|SaleFailed|Poor$|NotEnoughGold|NoGoldForMax|NoBow|NoPotion|"
                r"NoMoreContest|Talk04a$"),
    ("after", r"Idle\d?$|Post2$|^SwordsmanEnd$|AfterQuest|^HorvathTalk05$|Escort$|ForemanF|^ForemanE$|"
              r"MayorsGuardPost2|MineGuardC|SaleSuccessful|ConManIdle"),
    ("completion", r"Returned|Reward|Post$|Thanks$|Happy$|Finish|Success\d|Freed$|Thankful|Healed|^MayorFree$|"
                   r"HaveGoldForMax|ConManSale$|BecomeConjurer\d?$|ForemanD|Worker1Ji|^QuarterMaster12$"),
    ("reminder", r"Waiting|Prod\d?$|Pre\d?$|Impatient|HermitMeet02|ForemanC|^MayorBye$|Following|SalesPitch2|"
                 r"MaxWaiting|GearhartTalk0[456]$|HorvathPre|CaptainLeave|CaptainWaiting"),
    ("offer", r"Greeting|Greet\d?$|Intro|Quest$|Offer\d*$|Pitch|Meet01|Plea\d?$|Ask$|^ForemanA$|GearhartTalk0[12]|"
              r"MorganFriendTalk01|MaxTalk02|WardenTalk01|Worker1B|HorvathTalk01$|HorvathTalk01[ab]$|AidanGreet|"
              r"IngridScream|OldArchivist(Talk)?01|InversionBoyTalk01|^MayorsGuard$|ContestGuard$|Speech$|"
              r"CaptainTalkStart|HorvathTalk04$|LewisTalk01|Jandor0?1|JandorTalk01|Captain1$|Delwin1|MorganTalk0[24]$|"
              r"Horvath1$|CaptainGreet|Kalen"),
    ("guard", r"Guard|Gatekeeper|Warden|Jailer|Sentry|Watch"),
    ("shop", r"Shop|Vendor|Loreman|Bartender|Barkeeper|Gypsy|Mystic|^Max(Welcome|Talk01)|^Belfor$|BarMaiden|Grillf|"
             r"AppleMan|Loproc|^Garret$|Undertaker|BrightBlades|Kincaid|Henrick(SalesPitch|NoMore|NotEnough)|"
             r"^MaxTalk01$|BarTalk|^Mlurgh|GiftShop"),
    ("townsfolk", r"Towns(wo)?man|Maiden\d*Talk|Women|Rumor|^RandomSay$|^T\dP|Villager|Lydia|Drunk|Civvy|Folk|"
                  r"Jorgan|Grunbar|Albi|Dorian|Speak|LeavingGalava|HecRaisesDead|CreaturesActUp|WarriorInIx|"
                  r"ScepterRemark|GauntletBrother|^Maiden\d$|Bartender0\d|InfoMage|MiscMage|Henrick|Reception|"
                  r"Ganem|SaveDunMir|ChickenTalk"),
]
_SITUATIONS = [(s, re.compile(p)) for s, p in _SITUATIONS]
# single keys the patterns get wrong
_OVERRIDES = {"War01A.scr:GearhartTalk03": "refusal", "Wiz02A.scr:WardenTalk02": "completion",
              "Wiz02A.scr:MaxTalk03": "completion", "War01A.scr:GearhartTalk07": "completion",
              "War07A.scr:MorganTalk06": "completion", "War07A.scr:MorganFriendTalk02": "completion",
              "Wiz01A.scr:HorvathTalk04": "completion", "Wiz02:OldArchivist03": "completion",
              "Wiz02:OldArchivistTalk03": "completion", "Wiz02B.scr:HorvathTalk03": "completion",
              "Wiz02A.scr:WardenTalk04": "completion", "Wiz01A.scr:HorvathTalk03": "reminder",
              "Wiz02B.scr:HorvathTalk02": "reminder", "Wiz02B.scr:HorvathTalk04": "offer",
              "Con02a:MayorsReward": "completion", "Con02a:BridgeGuardReward": "completion",
              "Con02a:BridgeGuardGuarding": "offer", "Con02a:MayorGreeting": "offer", "Con02a:MayorProd": "reminder",
              "War03b:MayorIntro": "offer", "War03b:MayorPost": "completion", "War03b:MayorPost2": "after"}


def situation(key):
    """The situation of a campaign string from its key."""
    if key.startswith("Journal:"):
        name = key.split(":", 1)[1]
        return "hint" if re.search(r"Hint|Label$", name) else "journal"
    if key.startswith("WarriorHint:"): return "hint"
    if key in _OVERRIDES: return _OVERRIDES[key]
    name = key.split(":", 1)[1] if ":" in key else key
    for s, rx in _SITUATIONS:
        if rx.search(name): return s
    return "talk"


def map_of(key):
    m = re.match(r"^((?:Con|War|Wiz)\d+[A-Za-z]?)", key, re.I)
    return m.group(1).capitalize() if m else ""


def speaker_of(key):
    """The speaker from the key name: "War07A.scr:MorganTalk01" -> "Morgan", "Con05A.scr:FarmerReturned" -> "Farmer"."""
    if ":" not in key: return ""
    name = key.split(":", 1)[1]
    name = re.sub(r"(Talk\d.*|Greeting|Greet\d?|Waiting|Returned|Idle|Huffy|Prod\d?|Intro|Pre\d?|Post\d?|Reward|"
                  r"Speech|Say\d?|Thanks|Following.*|Freed|Plea\d?|Ask|Escort|Healed|Leaving|Rumor\d+|Angry\d+|"
                  r"Offer\d*|Welcome\d+|Meet\d+|Happy|SalesPitch.*|Speak.*|\d+[A-Za-z]?)$", "", name)
    return name or key.split(":", 1)[1]


_cache = {}


def strings(path=CSF):
    """{key: text} of the whole string table."""
    if path not in _cache:
        from strings import read_csf
        _, entries = read_csf(path)
        _cache[path] = {e["id"]: e["vals"][0]["str"] if e["vals"] else "" for e in entries}
    return _cache[path]


def campaign(path=CSF):
    """[{key, map, speaker, situation, text}] for every campaign line and journal entry (titles "NPC:" left out)."""
    out, seen = [], set()
    for k, v in strings(path).items():
        if not (CAMPAIGN.match(k) or k.startswith("Journal:") or k.startswith("WarriorHint:")): continue
        if not v.strip(): continue
        out.append(dict(key=k, map=map_of(k), speaker=speaker_of(k), situation=situation(k), text=v,
                        dup=v in seen))
        seen.add(v)
    return out


def proper_nouns(path=CSF):
    """Westwood's proper nouns: NPC titles plus capitalised words met mid-sentence in the campaign's lines."""
    from metrics import COMMON_CAPS
    names = collections.Counter()
    for k, v in strings(path).items():
        if k.startswith("NPC:") and v.strip():
            for w in re.split(r"[ ,]+", v):
                if w and w[0].isupper() and w not in COMMON_CAPS: names[w] += 3
    for e in campaign(path):
        for w in re.findall(r"(?<=[a-z,;] )([A-Z][a-zü'A-Z]+)", e["text"]):
            w = re.sub(r"'s?$", "", w)
            if w not in COMMON_CAPS: names[w] += 1
    return {w for w, n in names.items() if n >= 1}


def main():
    rows = campaign()
    c = collections.Counter(r["situation"] for r in rows if not r["dup"])
    print(f"{len(rows)} campaign strings ({sum(1 for r in rows if not r['dup'])} distinct)")
    for s, n in c.most_common():
        ex = [r for r in rows if r["situation"] == s and not r["dup"]][:3]
        print(f"  {s:11s} {n:4d}   e.g. " + " | ".join(f"{r['key']}" for r in ex))


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
