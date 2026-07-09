# DTB Market Research — Planning Session Input

Paste this whole file into a new session to kick off a full planning session. It captures
the current state of the project and the roadmap Brock wants to build. Nothing here is a
request to start coding — it's the brief for a planning conversation.

## How to resume
Repo: https://github.com/HyphaLogic/dtb-market-research
Local: `~/Library/Mobile Documents/com~apple~CloudDocs/dtb_market_research`
Verify state on arrival: `set -a; . ./.env; set +a` then
`python3 benchmark/score.py v4_output.csv` (needs the venv at `~/.venvs/dtb` and photos
rebuilt via `python data/download.py` — photos are gitignored, not in the repo).

## Where the project stands (as of this session)
- **Extractor is solved.** `extractors/extract_v4.py` = hybrid vision extractor: U²-Net
  crops the garment, sends it to the Claude API (`claude-opus-4-8`) with a structured-output
  schema, returns waistband color, ranked shorts colors, and the Frame+Base+Accent archetype.
- **Accuracy is validated.** 6 rounds of Brock-labeled ground truth (93 labels in
  `benchmark/ground_truth/`). Round-6 blind validation graded ~97% (100% on the hardest
  multi-color cases). v4 is trusted; the pixel-clustering lineage (v2.x/v3) is retired-for-history.
- **Full dataset exists.** v4 has been run on all 288 first-callout MP athletes from 9
  national shows (2025–2026). Zero errors. Outputs: `v4_output.csv` (gitignored working copy),
  `analysis/v4_full_run.csv` (committed snapshot), `analysis/v4_trends.csv` (aggregated trends).
- **Trend analysis works.** `analysis/trends_v4.py` produces color frequency (presence +
  coverage-weighted), waistband distribution, Frame/Base/Accent breakdown, color pairings,
  and by-year/by-tier cross-tabs. Headline market facts: black in 66% of shorts / 32% of
  design area; black waistband 59%; black frame 52%; base treatment solid 46% / gradient 27% /
  energy-element 12%; sweet spot = black-framed 3-color gradient with a graphic accent.
- **First product test done.** Graded Different Breed's "Disaster Series" (5 energy-element
  designs) against the market → B+/A−. Wildfire (orange/red, 36% lane) safest; Solar Storm
  (purple, 2% dominant) boldest whitespace/highest variance. Already at the wholesaler; the
  drop's sell-through becomes real ground truth for the trend model.

## Key facts / gotchas for whoever plans this
- API key is a standard `sk-ant-api03-` key in `dtb_market_research/.env` (gitignored as
  `.env`/`.env.*`). NOT an OAuth `ant` login — the raw key authenticates directly.
- score.py `strict` shorts metric understates v4: Brock names the black FRAME color first,
  the model reports largest-area-first, so ~80% of "strict misses" are ordering, not errors.
  The honest accuracy number is "primary color present anywhere in the read."
- Structured-output JSON schema rejects `minItems`/`maxItems` on arrays (400) — don't add them.
- Collectors (`extractors/collect_top5.py`, `collect_all.py`) currently HARDCODE 9 national
  shows. Weekly automation needs these generalized to discover shows off the NPC calendar.
- No NPC photos in the repo (copyright). `top5_photos/` is gitignored; rebuilt via download.py.

## The roadmap Brock wants to plan (in rough priority order)
1. **Mini trend dashboard.** A visual dashboard analyzing the trends (color frequency,
   archetype distribution, over-time shifts, by-show/by-division). Decide: static HTML
   artifact vs. a small hosted app; how it consumes v4_trends.csv; refresh cadence.
2. **Weekly in-season automation.** Scheduled job that pulls NPC MP-division results as shows
   happen — NOT just national-level; regional/state shows too. This means: generalize the
   collectors to walk the NPC contest calendar, filter to MP division, download first-callout
   photos, run extract_v4 on new athletes, append to the dataset. Plan the schedule (cron /
   scheduled agent), dedup against already-processed athletes, and cost control on the API.
3. **Expand the database analysis.** Grow beyond 288 as weekly data lands; richer analysis
   (brand/backdrop registries already exist in `registry/`; per-brand design tendencies;
   winner vs. non-winner design correlation; seasonal/regional differences).
4. **Automate the trend update.** Wire the weekly pull → extract → re-aggregate trends →
   refresh dashboard, end to end. **Brock wants to move compute off the pure-API path onto a
   Mac Mini** where possible (e.g. run U²-Net segmentation and orchestration locally; keep
   only the vision read on the API, or evaluate a local VLM for cost). Plan what runs where.
5. **Content / blog / social.** Use the trend findings to create a blog + social media posts
   about MP board-short trends and fashion. Goal: spread awareness of trends and funnel that
   attention back to the Different Breed site for sales. Plan: content format, cadence,
   which trend cuts make good posts, how it ties to product drops.

## Suggested planning outputs to produce in that session
- A phased plan (dashboard first? automation first?) with dependencies called out.
- Architecture decision for the Mac Mini split (what's local vs. API) and its cost model.
- The collector-generalization design (how to discover non-national NPC MP shows reliably).
- A content calendar concept tying trend cuts to Different Breed drops.
- Open questions for Brock to answer before build (hosting, budget, cadence, brand voice).
