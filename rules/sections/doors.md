# Doors

Schema (`rules/out/doors.json`): `types[name] = {kind: single|double, share_two_cell, share_one_cell, weighted_count, maps}`; `double_placement` / `single_placement` (hinge corners per wall direction); `jamb_facing` (how pieces beside an opening are shaped, with evidence).

## Single and double doors

Double doors are two half-door objects hinged at the two outer ends of a 2-cell opening (East + West in `/` walls, North + South in `\` walls). Single doors fill a 1-cell opening.

| Door type | Kind | 2-cell share | 1-cell share | Weighted count | Maps |
|---|---|---|---|---|---|
| Gate | double | 96% | 1% | 155.7 | 67 |
| WoodAndSteelHalfDoor | double | 100% | 0% | 135.7 | 46 |
| DunMirDoor | single | 18% | 82% | 126.7 | 14 |
| GalavaHalfDoor | double | 97% | 0% | 111.0 | 17 |
| ArchedHalfDoor | double | 99% | 0% | 92.7 | 23 |
| JailDoor | single | 36% | 64% | 84.0 | 25 |
| ArchedDoor | single | 0% | 100% | 73.2 | 22 |
| WoodenDoor | single | 31% | 69% | 70.0 | 15 |
| DunMirHalfDoor | double | 100% | 0% | 70.0 | 10 |
| CryptDoor | double | 86% | 11% | 63.0 | 12 |
| ThinWoodenDoor | double | 62% | 36% | 59.3 | 22 |
| CryptGate | double | 78% | 19% | 55.0 | 12 |
| BandedPlankDoor | double | 63% | 37% | 38.0 | 27 |
| IronFenceGate | double | 56% | 44% | 36.3 | 19 |
| SpikedDoor | single | 40% | 53% | 30.0 | 13 |
| GalavaDoor | single | 0% | 100% | 30.0 | 13 |
| LOTDHalfDoor | double | 100% | 0% | 28.0 | 13 |
| BandedWoodenDoor | single | 4% | 86% | 25.7 | 17 |
| OgreCageDoor | double | 80% | 20% | 25.0 | 10 |
| WoodAndSteelDoor | single | 0% | 100% | 24.0 | 7 |
| LOTDSingleDoor | double | 60% | 40% | 20.0 | 10 |
| BarredGate | double | 73% | 24% | 16.5 | 20 |
| Dilapidated | single | 29% | 71% | 14.0 | 5 |
| ThickWoodenDoor | single | 0% | 100% | 11.5 | 12 |
| SecretDoor | single | 0% | 100% | 2.0 | 2 |

## Wall pieces beside an opening

Facings of the walls next to a door opening are computed as if the opening were wall: 32.0% of jamb pieces match only that way, 1.0% only the other way (65.6% are the same either way). Computing them without the opening turns corners into straight pieces and Ts into corners, leaving see-through gaps.
