"""Signs the player reads (QA round 1, nox1 and nox10, 2026-10-13).

What the game does with a sign: clicking it sends the sign's text key to the client, which prints "The sign reads: %s"
(use.c:SignSays) on one centred line (opennox legacy/client__network__inform.c, case 0xF). So:
- a line break in the text is dropped, not drawn: "THE OLD BRIDGE\\nTo the mill." read "THE OLD BRIDGETo the mill."
  (nox1). Westwood's 273 campaign signs are all one line, 99 characters at most.
- the message is formatted into a buffer of 256 wide characters with no bound (nox_swprintf into v63[256]): a text
  over 239 characters writes past it and the client crashes to the desktop (ModLab's M2 sign, 274 characters).
- the large plank signs (PlankSign1-4) are boards on posts as tall as a man; Westwood stands one in 107 maps. The user:
  "this large style sign does not look good. Use the smaller ones instead, always." The kit stands Sign1 and Sign2.

    from kit.signs import SIGN, one_line, problem
    key = q.text("THE OLD BRIDGE\\nTo the mill.", "Sign")       # QuestBook folds a sign's text to one line
    camps.signpost(m, land, at, key)                            # a small sign (Sign1)
"""
import re

SIGN = "Sign1"                              # the small standing sign the kit uses (Westwood: 34 Sign1/Sign2 in campaign)
SMALL = ("Sign1", "Sign2")
LARGE = re.compile(r"^PlankSign\d")         # the tall plank boards: never
SIGN_WARN = 120                             # characters: over Westwood's longest (99) by a margin, a long read
SIGN_MAX = 200                              # characters: the client's buffer overflows past 239; keep well inside it
PREFIX = "The sign reads: "                 # use.c:SignSays, what the client prints before the text


def one_line(text):
    """A sign's text on one line: the lines joined so they read apart ("THE OLD BRIDGE - To the mill."). A line that
    ends a sentence (or a clause) is followed by a space; a heading by " - "; a line that starts in lower case goes on
    the sentence before it; a signature line ("- Ilsa Rook") keeps its own dash."""
    lines = [re.sub(r"\s+", " ", l).strip() for l in str(text).split("\n")]
    lines = [l for l in lines if l]
    if not lines: return ""
    out = lines[0]
    for l in lines[1:]:
        if out[-1] in ".!?:;,-" or l.startswith("-") or l[0].islower(): out += " " + l
        else: out += " - " + l
    return out


def problem(text):
    """(severity, why) when a sign's text cannot be read as meant, else None."""
    if text is None: return "error", "has no text the game knows (the key is in no string table)"
    if not text.strip(): return "error", "reads nothing (its text is empty)"
    if "\n" in text or "\r" in text:
        return "error", "has a line break, which the game drops: the lines run together"
    if len(text) > SIGN_MAX:
        return "error", (f"reads {len(text)} characters: over {SIGN_MAX}, near the client's limit (past 239 it crashes "
                         f"to the desktop)")
    if len(text) > SIGN_WARN:
        return "warning", f"reads {len(text)} characters: Westwood's longest is 99 (keep a sign to a line, {SIGN_WARN} at most)"
    return None
