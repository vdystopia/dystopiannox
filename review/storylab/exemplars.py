"""The writers' exemplars: 20-30 of Westwood's own campaign lines per situation, for imitation.

    py review/storylab/exemplars.py        writes review/storylab/exemplars/<situation>.md from nox.csf (read only)

The lab's writers imitate these (rhythm, register, corniness, how people are named) rather than follow rules alone.
None of them is in a blind packet: every key a scenario's Westwood pool uses (scenarios.json, "westwood" and
"control_extra") is left out, so a writer never sees the lines its text is judged beside. A near-copy of a line in a
pool (the same speech in two chapters) is left out by hand.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import westwood  # noqa: E402

OUT = os.path.join(HERE, "exemplars")

# situation -> (title, how to read them, [(group heading, [keys])])
EXEMPLARS = {
    "offer": ("Quest offers (a giver's first words)",
              "Most start in the middle of the trouble or with a stock greeting, not with a self-introduction. Some "
              "are a page, some three. Not all end on a question; not all say why the giver cannot go.", [
        ("The trouble shouted first", ["Con02a:MayorsGuard", "Con07B.scr:WardenTalk01", "Con02a:MayorCall",
                                       "War05A.scr:IngridScream", "Con07C.scr:OpeningHelp"]),
        ("A victim begs", ["War09a:AidanGreet1", "War09a:AidanGreet2", "War09c:CainPlea", "War09c:CainAsk",
                           "War03c:KalenSpeech"]),
        ("An official or a mentor explains", ["Con02a:AldwinImp", "War03b:AldwynIntro", "Con03B.scr:Worker1B",
                                              "Wiz07.scr:WardenTalk01", "Con02a:ContestGreeting"]),
        ("A deal, a pitch, a bargain", ["War07A.scr:MorganTalk02", "War08b:HenrickSalesPitchB", "War05A.scr:GypsyGreeting",
                                        "Con02a:Gatekeeper2Greet"]),
        ("Gossip that turns into a pointer", ["Con02a:BarkeeperQuest", "War08a:BarkeeperGreet", "War06a:HorrendousPride"]),
    ]),
    "opening": ("The main quest opened (captains, mentors, masters)",
                "Orders, not requests: where to go, whom to find, what to bring back, and the chapter's villain named. "
                "Often 'lad'. Grand words beside plain ones.", [
        ("Arrival and orders", ["Wiz01A.scr:JandorTalk01", "Wiz01A.scr:JandorTalk02", "Con07A.scr:Jandor01",
                                "War07A.scr:JandorTalk01", "Wiz07.scr:JandorTalk01", "Wiz02A.scr:Horvath1",
                                "Wiz06b:Delwin1", "War03b:AirshipCaptainIxSpeech", "Wiz08a:CaptainGreet"]),
        ("The great ones", ["War02A.scr:RealTalk1Start", "Con08a:AldwynGreet", "Wiz07.scr:HorvathTalk01",
                            "Con07H.scr:MarikTalk02", "Con03A.scr:JandorA"]),
        ("Asides and sendoffs", ["War01a:CaptainTalk2cStart", "War01a:CaptainTalk2dStart", "Wiz03a:AirshipCaptainSendoff",
                                 "War09a:CaptainLeave", "War07:JandorEnd", "War01a:CaptainTalk2eStart"]),
    ]),
    "reminder": ("Reminders (while the quest is open)",
                 "Short. Impatience, worry, the ask again, a vague remark, now and then a hint. Rarely the way again.", [
        ("Impatience", ["Con02a:AldwinProd", "War03b:MayorBye", "Con08:AldwynProd", "War02A.scr:RealTalk2Start",
                        "Con02a:ContestOfficialWaiting", "Con02a:MeetTheMayor"]),
        ("Worry and urgency", ["Wiz05C.scr:HorvathWaiting", "War05C.scr:MaidenWaiting", "War08a:PriestProd4",
                               "Con08a:PriestProd3"]),
        ("The ask again", ["Con02a:ConManSalesPitch2", "War01A.scr:GearhartTalk04", "War09a:AidanWaiting",
                           "War02a:GearhartTalk05"]),
        ("A remark or a hint", ["War01A.scr:GearhartTalk05", "War03b:AldwynPre", "War03b:BarkeeperPre",
                                "War03b:BridgeGuardPre", "Con08:AldwynProd2", "War02a:GearhartTalk04"]),
    ]),
    "completion": ("Thanks and rewards",
                   "Delight or relief first, then thanks, then the reward said plainly; a big one points on to what is "
                   "next. Stock phrases are used straight.", [
        ("Joy", ["Con02a:MayorFree", "War05A.scr:FarmerWifeGreeting", "War05B.scr:SisterReturned",
                 "War05A.scr:FrogThanks", "War02A.scr:HorrendousTalk3Start", "Con03a:MineWorkerThanks"]),
        ("Thanks and the reward", ["Con02a:AwardContestPrize", "War09a:AidanThankful", "War09c:CainHealed",
                                   "Wiz05B.scr:HorvathReturned", "Wiz05C.scr:HorvathFreed", "Wiz02B.scr:HorvathTalk03",
                                   "War02A.scr:GearhartTalk1Start"]),
        ("And on to what is next", ["Con03B.scr:Worker1Ji", "War03b:BridgeGuardPost", "War05B.scr:CaptainSuccess2",
                                    "War05B.scr:CaptainSuccess3", "War03b:AldwynPost", "Wiz02:OldArchivistTalk04"]),
        ("Afterwards, from townsfolk", ["War03b:T1Post", "War03b:T2Post", "Con02a:ScoreKeeperThanks"]),
    ]),
    "after": ("Afterwards and refusals",
              "Afterwards: a few words, often the same stock thanks. Refusals: a sulk, a shrug, or the terms again.", [
        ("Afterwards", ["War05A.scr:FarmerWifeIdle", "War05A.scr:IngridIdle", "War05A.scr:FrogIdle",
                        "War05A.scr:SwordsmanEnd", "War05B.scr:SisterIdle", "Wiz05B.scr:CaptainIdle",
                        "Wiz05B.scr:HorvathIdle", "Wiz05C.scr:CaptainIdle", "War09c:CainEscort",
                        "Con02a:BarkeeperAfterQuest", "Con02a:MayorsGuardIdle", "Con03C.scr:ForemanE",
                        "War03b:AldwynPost2", "Con02a:ConManIdle", "Con02a:ConManIdle2", "War05A.scr:SadVillagerDeadIdle"]),
        ("Refusals and no gold", ["Con02a:AldwinPoor", "Con02a:ConManNotEnoughGold", "Con02a:NotEnoughGold",
                                  "Con02a:NoMoreContestTries", "War07A.scr:NoGoldForMax", "War08b:HenrickNotEnoughGold",
                                  "War09c:CainNoPotion", "War01A.scr:QuarterMasterTalk02"]),
    ]),
    "townsfolk": ("Townsfolk: rumours, gossip, barks",
                  "Mostly colour: brush-offs, worries, gossip about the great, tips, flirting, complaints. Now and then "
                  "a word about the map's trouble, in general terms. Uneven: a two-word line beside a run-on.", [
        ("Brush-offs", ["War02a:NewTownsman1", "War02a:NewTownsman2", "War02a:NewTownsman5", "War02a:NewTownswoman2",
                        "War02a:NewTownswoman3", "War03b:T4Pre"]),
        ("The times", ["Con05:Townsman11Talk02", "War06a:WomenSpeak3", "Wiz02A.scr:MaidenTalk05",
                       "War01A.scr:Townsman5Talk01", "Wiz02A.scr:MaxRumor03", "Con07:MiscMage03"]),
        ("Gossip and opinion", ["War01A.scr:Maiden1Talk02", "Wiz07:Ganem01", "War06a:WomenSpeak2",
                                "War06a:SlainSpeakW2", "Wiz02A.scr:MaxRumor02", "Con02A:Townsman3Talk01",
                                "Con02A:HenrickTalk03", "Con02A:HenrickTalk02"]),
        ("Flirting, teasing, crude", ["War01A.scr:LydiaTalk01", "War01A.scr:LydiaTalk03", "War06a:WomenSpeak4",
                                      "War06a:SlainSpeakT1", "Wiz02A.scr:MaidenTalk03", "War07A.scr:DrunkardTaunt01"]),
        ("About the map's trouble", ["Con02A:Townsman1Talk02", "Con02A:Townsman4Talk02", "War01A.scr:Townsman3Talk02",
                                     "Wiz02:InfoMage01", "War02A.scr:ChickenTalk1Start"]),
        ("After the quest", ["Con02A:Townsman4Talk01", "Con02A:Maiden2Talk01", "Con02A:Townsman3Talk03"]),
    ]),
    "guard": ("Guards, gatekeepers, wardens",
              "Rules, warnings, directions, pride in the place, curt orders. Short imperatives.", [
        ("Welcome and pointer", ["Con02a:Gatekeeper3Greet", "War03a:IxGuard2Intro", "Con08a:GuardGreet",
                                 "War03b:GatekeeperPre", "War03b:ContestGuard"]),
        ("Rules and threats", ["Con02A:JailerTalk02", "Con02A:JailerTalk03", "Wiz02A.scr:WardenTalk06",
                               "War07A.scr:WardenPreArrest01", "War07A.scr:WardenPreArrest03",
                               "Wiz02B.scr:ArchivistTalk02", "Wiz02B.scr:ArchivistTalk03", "Wiz02B.scr:ArchivistTalk04"]),
        ("Curt", ["War01A.scr:GateGuard1Talk02", "War01A.scr:Guard2Talk1aStart", "War01A.scr:Guard1Talk1aStart",
                  "War01A.scr:Guard1Talk1bStart", "War01A.scr:Guard2Talk1bStart"]),
        ("Orders", ["War02A.scr:GuardTalk1Start", "War02A.scr:GuardTalk2Start", "War03a:IxGuard2End",
                    "War02A.scr:GuardSay1Start"]),
    ]),
    "shop": ("Shopkeepers, barkeepers, pedlars",
             "A flat slogan, a pitch, a wink at the price or the times, a grumble. A town's keepers have nothing to do "
             "with each other.", [
        ("Slogans", ["Wiz02A.scr:ShopkeeperTalk01", "Wiz02B.scr:GiftShopVendorTalk01", "Con07B.scr:BookVendorTalk01",
                     "Wiz02A.scr:LoremanTalk01", "War03a:Garret", "War05A.scr:ShopKeeperTalk2"]),
        ("Barkeepers", ["Con05A.scr:BartenderTalk2", "Con05:Bartender02", "War02A:BartenderTalk1bStart",
                        "War02A:BartenderTalk1fStart", "War02:BartenderTalk1dStart", "War02B.scr:BarTalk1",
                        "War05A.scr:BartenderTalk2", "Con02a:BarMaiden", "Con02a:BarMaiden2"]),
        ("The times and the trouble", ["Con07B.scr:ShopkeeperTalk01", "Con07B.scr:LoremanTalk01", "Wiz07:MlurghTalk01",
                                       "War06a:ShopKeeper", "Con07B.scr:BrightBladesTalk01", "Con07B.scr:MageVendorTalk01"]),
        ("Odd ones", ["Wiz02A.scr:UndertakerTalk01", "Con07B.scr:UndertakerTalk01", "Con07B.scr:AppleManTalk01",
                      "Wiz02A.scr:AppleManTalk02", "War04a:Loproc", "Wiz06b:Shopkeeper1", "War08a:Mystic"]),
    ]),
    "captive": ("Captives found, following, freed",
                "Found: a cry, then the plea in a sentence. Following: one urgent line, sometimes a hint. Plain.", [
        ("Found", ["Con03a:MineWorkerHelp", "Con03B.scr:WorkersTalkAKey", "War02a:GearhartTalk01",
                   "Wiz05C.scr:Horvath1", "War09a:AidanPlea", "War09c:CainPlea2", "Con05A.scr:FrogTalk2",
                   "War07A.scr:MorganTalk01", "Con03B.scr:Worker1A"]),
        ("Following", ["Con03a:MineWorkerLead", "Con03a:MineWorkerTake", "War05B.scr:SisterFollowing3",
                       "War05C.scr:SisterFollowing1B", "War05C.scr:SisterFollowing1C", "War05C.scr:SisterFollowing1E",
                       "War05C.scr:SisterFollowing2", "Wiz05B.scr:HorvathEscorting", "War07A.scr:MorganTalk05",
                       "Con03B.scr:WorkersStop", "Con03B.scr:WorkersTalkB"]),
        ("Freed", ["Con03B.scr:WorkersReturn", "Con03B.scr:WorkersTalkC", "War05B.scr:SisterFreed",
                   "War05C.scr:MaidenScream2", "War05C.scr:MaidenScream4", "War07A.scr:MorganTalk03",
                   "Wiz05B.scr:HorvathFreed", "War09a:AidanLeaving"]),
    ]),
    "journal": ("Journal entries",
                "One order, 5-14 words. The goal, and the place only when the goal needs it. Never 'I'. A NOTE for "
                "news.", [
        ("Go, find, meet", ["Journal:FindHorvath", "Journal:MeetHorvath", "Journal:LocateMineForeman",
                            "Journal:Chapter8MeetCaptain", "Journal:Chapter8LocateAldwyn", "Journal:Con03FindAirshipCap",
                            "Journal:War2Academy", "Journal:FirstQuest", "Journal:FindQuarterMaster",
                            "Journal:SponsorQuest", "Journal:Wiz6Bull", "Journal:FindTunnel", "Journal:FindOutpost"]),
        ("Fetch", ["Journal:GetBookOfOblivion", "Journal:GetHON", "Journal:ReturnToHorvath", "Journal:Wiz05Quest5",
                   "Journal:War10aOrbQuest", "Journal:ArchivistBook", "Journal:Con05Quest1B"]),
        ("Fight, survive, rescue", ["Journal:GauntletQuest", "Journal:War2Sewer", "Journal:War05Quest1",
                                    "Journal:War05Quest6", "Journal:Wiz6Wizards", "Journal:Chapter4Escape",
                                    "Journal:War6Necro", "Journal:Con10Quest1"]),
        ("Notes", ["Journal:War05BridgeGuard", "Journal:War05SisterFound", "Journal:War11Drain"]),
    ]),
}


def pool_keys():
    d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
    out = set()
    for s in d["scenarios"]:
        for u in s["westwood"] + s.get("control_extra", []):
            for _, k in u:
                out.update(k if isinstance(k, list) else [k])
    return out


def build():
    S = westwood.strings()
    pool = pool_keys()
    os.makedirs(OUT, exist_ok=True)
    report = []
    for sit, (title, how, groups) in EXEMPLARS.items():
        L = [f"# {title}", "",
             "Westwood's own lines (Nox, 1999), from the campaign's string table. Imitate their rhythm, register, "
             "corniness and how people are named; never copy a line or reuse a Westwood name. " + how, "",
             "A page break inside a speech shows as ` / `. The key says who speaks and where (Con = Conjurer, War = "
             "Warrior, Wiz = Wizard campaign; the number is the chapter).", ""]
        n = 0
        for head, keys in groups:
            L += [f"## {head}", ""]
            for k in keys:
                if k in pool:
                    report.append(f"{sit}: {k} is in a packet pool, left out"); continue
                if k not in S:
                    report.append(f"{sit}: {k} not in the string table"); continue
                t = re.sub(r"\s*\n\s*\n\s*", " / ", S[k].strip()).replace("\n", " ")
                L.append(f"- {t}  `{k}`"); n += 1
            L.append("")
        open(os.path.join(OUT, f"{sit}.md"), "w", encoding="utf-8").write("\n".join(L))
        report.append(f"{sit}: {n} lines")
    print("\n".join(report))


if __name__ == "__main__":
    build()
