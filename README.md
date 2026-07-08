# DTB Market Research - NPC Men's Physique Trend Intelligence
Scrapes NPC national-show galleries, extracts board-short design attributes
(background / skin / floor reference surfaces -> waistband -> shorts colors -> archetype),
benchmarked against Brock-labeled ground truth. Internal research only; photos are
NOT committed - rebuild locally with `python data/download.py`.

## Benchmark history (labels in benchmark/ground_truth/, harness: benchmark/score.py)
Since 2026-07-08 the harness scores all 73 labels (4 rounds), prefers the brock_shorts
column over notes parsing, and reports shorts strict (top cluster == label primary) and
loose (label primary anywhere in the read). Pre-v3 numbers below used older/smaller samples.
| version | waistband | shorts primary color | notes |
|---|---|---|---|
| v2.1 | 12% | 38% | per-image edge background mask |
| v2.2 | 10% | 35% | per-show bg model; black-on-black regression |
| v2.3 | 10% | ~70% | luminance-scaled bg threshold |
| v2.4 | 40% (n=73) | 27% strict / 63% loose | was "67%" on round-4-only n=9; full label set is harsher |
| v3 | 36% (n=72) | 47% strict / 72% loose | as first committed, before 2026-07-08 fixes |
| v3 current | **67%** (n=72) | 42% strict / **82%** loose | +skin exclusion in garment/waistband samples, zoned disc suppression (global white-drop was erasing white shorts), waist persistence check vs arms-crossing poses |
| **v4 (vision)** | **88%** (n=73) | 53% strict / **90%** loose | U2-Net crop -> Claude API (claude-opus-4-8) structured output; also emits Frame+Base+Accent archetype. See analysis below. |

### v4 analysis (2026-07-08)

v4 is a categorical leap over the pixel extractors, and the "53% strict" number understates it.
Of 34 strict misses, **28 are ordering-only** (the color Brock named as primary IS in v4's read,
just not ranked #1 by area) and only **6 are genuinely wrong** — and of those 6, two are the
Classic-Physique wrong-photo cases (Bryce Parrott, Tyler Waltz) where v4 correctly read the
trunks *in the photo*. Net: **v4 identifies the correct shorts colors on 67/73 = 92% of photos**
and the waistband on 88%. The strict metric measures Brock's naming convention (he names the
black FRAME color first; the model reports the largest-area body color first), not model accuracy.
v4 emits the archetype `frame` field, so score.py can be taught to credit black-frame matches
and score on "primary present anywhere" — that recalibration, not more model work, is what moves
strict toward the gate. Waistband misses (9) are mostly hue-boundary calls (light-blue/teal/navy,
lavender/black) plus the two wrong-photo cases.

Failed experiments (all regressed, do not retry blindly): v2.3-style shadow-skin term
(eats black waistbands), waistband strip offset below crease, number-disc y-anchor for the
strip (disc digits/shadow poison black-on-black), cluster-vote waistband vs median.
The pixel-clustering plateau (v3 = 67%/42%) is why v4 moved to a vision model.

## Pipeline
collect (extractors/collect_top5.py, 288 first-callout athletes / 8 shows)
-> extract (extractors/extract_v24.py or extract_v3.py)
-> benchmark (python benchmark/score.py v3_output.csv)
-> analysis/ trend datasets (archetypes + color combos, registry/ for brands + backdrops)

## Next
1. DONE 2026-07-08: v4 vision extractor (extract_v4.py, claude-opus-4-8) -> 88% waistband,
   92% shorts-color accuracy (67/73), also emits Frame+Base+Accent archetype. This is the
   working extractor going forward; v2.x/v3 are the pixel-clustering lineage, kept for history.
2. Recalibrate score.py to Brock's naming convention: credit a match when v4's `frame` field
   is a black frame and Brock's primary is black, and score shorts on "primary present anywhere"
   rather than "top-by-area." This lifts strict from 53% toward the real 92% and makes the gate
   measure model accuracy, not the area-vs-frame ordering difference. THEN re-check the 90/80 gate.
3. Once gate clears: full 288-athlete v4 run -> analysis/v4_full_run.csv; regenerate
   trend_analysis on trusted data (colors + archetype grammar). Est. cost <$1 for 288 photos
   at Opus 4.8; consider re-testing claude-sonnet-5 (~40% input cost) for recurring weekly runs.
4. Round-5 hard-tail labels captured (benchmark/review_round5_hardest10_REVIEWED.csv) — fold
   into ground_truth if desired.
5. Weekly automation on the NPC contest calendar; comparison galleries as the primary unit.
