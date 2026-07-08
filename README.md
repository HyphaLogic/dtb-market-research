# DTB Market Research - NPC Men's Physique Trend Intelligence
Scrapes NPC national-show galleries, extracts board-short design attributes
(background / skin / floor reference surfaces -> waistband -> shorts colors -> archetype),
benchmarked against Brock-labeled ground truth. Internal research only; photos are
NOT committed - rebuild locally with `python data/download.py`.

## Benchmark history (labels in benchmark/ground_truth/, harness: benchmark/score.py)
| version | waistband | shorts primary color | notes |
|---|---|---|---|
| v2.1 | 12% | 38% | per-image edge background mask |
| v2.2 | 10% | 35% | per-show bg model; black-on-black regression |
| v2.3 | 10% | ~70% | luminance-scaled bg threshold |
| v2.4 | 67% (n=9) | - | Brock's spec: bg+skin+floor written out, top-down waist->hem scan |
| v3 | TBD | TBD | U2-Net segmentation + geometric garment region (probe validated on Edwards) |

## Pipeline
collect (extractors/collect_top5.py, 288 first-callout athletes / 8 shows)
-> extract (extractors/extract_v24.py or extract_v3.py)
-> benchmark (python benchmark/score.py v3_output.csv)
-> analysis/ trend datasets (archetypes + color combos, registry/ for brands + backdrops)

## Next
1. Benchmark v3 across all labels (gate: 90% waistband/surfaces, 80% shorts primary)
2. Full 288-photo run -> regenerate trend_analysis on trusted data
3. Weekly automation on the NPC contest calendar; comparison galleries as the primary unit
