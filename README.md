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

Failed experiments (all regressed, do not retry blindly): v2.3-style shadow-skin term
(eats black waistbands), waistband strip offset below crease, number-disc y-anchor for the
strip (disc digits/shadow poison black-on-black), cluster-vote waistband vs median.
Known residual failure modes: colored band under drawstring/crease shadow reads black;
shadowed dark skin reads brown on black bands; lavender/gray/magenta boundary confusions;
"primary color" semantics differ (Brock lists frame color first, machine reports largest
pixel area) - this caps the strict shorts metric, loose is the truer extraction signal.

## Pipeline
collect (extractors/collect_top5.py, 288 first-callout athletes / 8 shows)
-> extract (extractors/extract_v24.py or extract_v3.py)
-> benchmark (python benchmark/score.py v3_output.csv)
-> analysis/ trend datasets (archetypes + color combos, registry/ for brands + backdrops)

## Next
1. DONE 2026-07-08: v3 benchmarked across all labels -> 67% waistband / 42% strict, 82% loose
   shorts. Gate (90% waistband / 80% shorts strict) NOT cleared; pixel-heuristic iteration
   plateaued (see failed experiments above). Full 288 trend run stays gated.
2. Brock labels benchmark/review_round5_hardest10.csv (10 hardest unlabeled cases by
   difficulty signals) -> becomes round5 ground truth for the hard tail.
3. To clear the gate: heuristics look tapped out; next candidates are a vision-model read
   of the garment crop (claude_vision_read column exists in round1 labels for this) or a
   small trained classifier, benchmarked with the same harness.
4. Weekly automation on the NPC contest calendar; comparison galleries as the primary unit.
5. Archetype grammar (registry/taxonomy.md Frame+Base+Accent) not yet machine-emitted.
