# Doors

Schema (`rules/out/doors.json`): `types[name] = {kind: single|double, share_two_cell, share_one_cell, weighted_count, maps}`; `double_placement` / `single_placement` (hinge corners per wall direction); `jamb_facing` (how pieces beside an opening are shaped, with evidence).

## Single and double doors

Double doors are two half-door objects hinged at the two outer ends of a 2-cell opening (East + West in `/` walls, North + South in `\` walls). Single doors fill a 1-cell opening.

| Door type | Kind | 2-cell share | 1-cell share | Weighted count | Maps |
|---|---|---|---|---|---|
| Gate | double | 96% | 1% | 163.7 | 70 |
| WoodAndSteelHalfDoor | double | 100% | 0% | 141.7 | 48 |
| DunMirDoor | single | 24% | 76% | 140.7 | 22 |
| GalavaHalfDoor | double | 98% | 0% | 131.0 | 20 |
| CryptDoor | double | 82% | 17% | 125.0 | 22 |
| ArchedHalfDoor | double | 99% | 0% | 104.7 | 27 |
| ArchedDoor | single | 0% | 100% | 89.2 | 26 |
| JailDoor | single | 34% | 66% | 88.0 | 26 |
| WoodenDoor | single | 28% | 72% | 79.0 | 16 |
| BandedPlankDoor | double | 58% | 42% | 79.0 | 35 |
| LOTDHalfDoor | double | 100% | 0% | 74.0 | 17 |
| CryptGate | double | 80% | 17% | 73.0 | 19 |
| LOTDSingleDoor | single | 17% | 83% | 71.0 | 14 |
| DunMirHalfDoor | double | 100% | 0% | 70.0 | 10 |
| SpikedDoor | double | 64% | 33% | 69.0 | 14 |
| ThinWoodenDoor | double | 61% | 37% | 60.3 | 23 |
| IronFenceGate | double | 56% | 44% | 43.3 | 25 |
| OgreCageDoor | double | 86% | 14% | 37.0 | 13 |
| GalavaDoor | single | 0% | 100% | 35.0 | 16 |
| BandedWoodenDoor | single | 3% | 88% | 31.7 | 21 |
| Dilapidated | double | 53% | 47% | 30.0 | 9 |
| BarredGate | double | 61% | 37% | 29.5 | 27 |
| WoodAndSteelDoor | single | 0% | 100% | 26.0 | 9 |
| AncientRuinDoor | double | 82% | 18% | 22.0 | 2 |
| ThickWoodenDoor | single | 0% | 100% | 14.5 | 15 |
| AncientDungeonDoor | double | 60% | 40% | 10.0 | 2 |
| SecretDoor | single | 0% | 100% | 2.0 | 2 |

## Wall pieces beside an opening

Facings of the walls next to a door opening are computed as if the opening were wall: 29.8% of jamb pieces match only that way, 0.7% only the other way (68.3% are the same either way). Computing them without the opening turns corners into straight pieces and Ts into corners, leaving see-through gaps.
