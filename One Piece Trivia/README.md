# One Piece Trivia

8-bit One Piece trivia voyage: 7 prompts, 25 seconds each (keep guessing until you hit an answer or time runs out), six bounty tiers
(Cabin Mate 10 → Pirate King 100), Reverse Mountain at 450, Elbaf at 700.

Live version (Claude artifact): https://claude.ai/artifact/HPK1rytdaaW73rkGHAap1S

**Modes**
- **Daily voyage:** the date picks the 7 prompts, so everyone gets the same ones that day. One try per day
  (remembered in that browser). This is the mode to compare scores with friends.
- **Free play:** random prompts, unlimited plays.

**Share button** (end of a voyage) copies a spoiler-free result for group chats, one square per prompt:
🟨 Pirate King · 🟪 Yonko · 🟦 Supernova · 🟩 Rookies · 🟧 Captain · ⬜ Cabin Mate · 🟥 time ran out

Note: the daily prompts depend on the prompt list, so everyone needs the same version of the game
(the same hosted link) for daily scores to match. Changing config/prompts.json changes the daily picks.

---

## Publishing the live site (one-time setup)
The `site/` folder is the website: `index.html` (the game), `og.png` (the preview image when you
paste the link in a chat) and `favicon.png` (the browser tab icon). `update.bat` refreshes
`site/index.html` every time it runs.

**1. Put the project on GitHub** (GitHub Desktop: https://desktop.github.com)
- File → Add local repository → choose `E:\Claude Code\One Piece Trivia`.
- It says it isn't a Git repository yet → click **create a repository** → name it `one-piece-trivia`
  → Create repository. (The `.gitignore` keeps wiki dumps and Python cache files out.)
- Click **Publish repository**. Private is fine; Vercel can still read it.

**2. Deploy it on Vercel** (https://vercel.com, same account as your portfolio)
- Add New → Project → Import the `one-piece-trivia` repo.
- **Root Directory: click Edit and choose `site`.** This is the one setting that matters.
- Framework Preset: **Other**. Leave the build and output settings empty.
- Deploy. You get a link like `one-piece-trivia.vercel.app` (rename it under Settings → Domains).

**3. Tell the updater your link** (for nicer previews in group chats)
- Open `update.py`, set `SITE_URL = 'https://your-link.vercel.app'`, run `update.bat`, commit and push.

## Updating the live site
1. Run `update.bat` (with or without a new wiki dump).
2. In GitHub Desktop, write a short summary (e.g. "Add 5 prompts") → **Commit to main** → **Push origin**.
3. Vercel redeploys automatically in about 30 seconds. Everyone gets the new version on refresh.

Changing prompts changes which seven the daily voyage picks, so avoid pushing prompt changes
in the middle of a day your friends are playing.

---

## Updating the game

**One-time setup:** install Python 3.9 or newer (python.org, tick "Add Python to PATH"), then run:

    python -m pip install py7zr

That lets the updater open .7z wiki dumps. (If you have 7-Zip installed it works without it.)

**When the wiki has new content:**
1. Download the new dump: go to https://onepiece.fandom.com/wiki/Special:Statistics, scroll to
   "Database dumps", download the **current pages** dump (`onepiece_pages_current_xml.7z`).
2. Drag the `.7z` file onto `update.bat`.
3. Read the window before closing it. Any `WARNING` line means one of your overrides didn't apply
   (usually because the wiki renamed a page). Fix the name in `config/overrides.json` and run again.
4. Open `one-piece-trivia.html` to check it, then publish it wherever the game is hosted.
   The online version does NOT update by itself.

**When you only changed prompts or overrides:** double-click `update.bat` with no file.
It reuses the last parsed wiki, so it takes a couple of seconds.

The updater rebuilds `data/prompts.json`, both CSVs in `exports/`, and `one-piece-trivia.html`.

---

## Adding a prompt
Add a line to `config/prompts.json`, then double-click `update.bat`. A prompt gets its answers from one or more of:

| Option | What it matches | Example |
|---|---|---|
| `categories` | Pages in these wiki categories (exact, plural name). Anime-only versions are added automatically. | `"categories": ["Swordsmen"]` |
| `infobox` | Every page using this infobox type | `"infobox": "Devil Fruit Box"` |
| `affiliations` | Characters whose infobox lists this group, including former members | `"affiliations": ["Whitebeard Pirates"]` |
| `include_former` | Set to `false` to drop former members of an affiliation | `"include_former": false` |
| `include_anime_only` | Set to `false` to drop anime-only answers | `"include_anime_only": false` |
| `devil_fruit_type` | Characters who ate a fruit of this type: `Paramecia`, `Zoan`, `Logia` or `any` | `"devil_fruit_type": "Zoan"` |
| `starts_with` | Characters with a name, name part (Luffy) or epithet (Pirate Hunter Zoro) starting with this letter. Only names starting with the letter are accepted. Add `"epithets": false` to ignore epithets. | `"starts_with": "P"` |
| `event` + `chapters` or `arc` | Characters who appear in those manga chapters, sorted by evidence into the review sheet (see below). `groups` adds crews/places that count as "Likely". | `"event": "Summit War of Marineford", "chapters": [550, 580]` |

The game shows at most one letter prompt per voyage (FAMILY_LIMITS in `source/template.html`).

Example:

    { "prompt": "Name a Whitebeard Pirate", "affiliations": ["Whitebeard Pirates"] }

Then open `exports/one-piece-trivia-all-answers.csv` and scan the new prompt's answers. Remove junk
entries with `exclude` in `config/overrides.json`.

Good prompts have 25+ answers (fewer makes the tiers coarse) and include the obvious famous answers.
To find category names, look at the bottom of any wiki page, or ask Claude to search `data/parsed-wiki.json`.

## Reviewing event prompts: reviews/event-review.csv
For "who was at Marineford / in Wano / on Egghead", the wiki doesn't say who was physically there,
only who appears in each chapter. The updater sorts everyone seen in those chapters:
- **Confirmed**: linked from the wiki's article about the event
- **Likely**: listed under a group that took part (e.g. Marines, Whitebeard Pirates)
- **Questionable**: only seen in the chapters. Often a cutaway (Supernovas watching from Sabaody).

Open `reviews/event-review.csv` in Excel. The `Keep` column decides who counts:
- `yes` = counts, `no` = doesn't count, `?` = not reviewed yet (doesn't count until you say yes)
- Questionable rows are at the top of each prompt. Change `?` to `yes` or `no`, save as CSV, run `update.bat`.
- You can also flip Confirmed/Likely rows to `no` (e.g. Rayleigh and Rouge for Marineford).
Your choices are kept across wiki updates. New characters from a new dump show up with defaults.
Cover pages, flashbacks and mentions are already left out.

## Your manual choices: config/overrides.json
Applied after every update, so a new wiki dump never erases them. Use prompt text exactly as in
prompts.json and answer names exactly as in the all-answers CSV.
- `pirate_king`: your Pirate King pick per prompt (anime-only answers aren't allowed)
- `tiers`: move one answer to a different tier (Cabin Mate, Captain, Rookies, Supernova, Yonko, Pirate King)
- `exclude`: remove answers from a prompt
- `aliases`: extra spellings or nicknames that should count

---

## How rarity is decided
Rarity comes from the wiki: for each answer, the updater counts how many other wiki articles link
to its page (each article counts once; nicknames and old page names are included).

For each prompt, all accepted answers are sorted from most-linked to least-linked and split by
position in that list, not by a fixed number of links:

| Position in the prompt's list | Tier | Points |
|---|---|---|
| Top 8% | Cabin Mate | 10 |
| 8–20% | Captain | 15 |
| 20–45% | Rookies | 30 |
| 45–75% | Supernova | 60 |
| Bottom 25% | Yonko | 85 |
| One answer per prompt | Pirate King | 100 |

The Pirate King is your pick from overrides.json, or otherwise the most-linked non-anime-only answer
in the Yonko group (rare, but something some players will actually think of). Anime-only answers
are tiered like the rest but can never be Pirate King. The same character can land in different
tiers in different prompts, because it depends on who else is in that list.
The cut-offs are `CUTS` at the top of `source/scripts/build_prompts.py`.

**Known weaknesses**
- Link counts measure how important a character is on the wiki, not what fans remember for that
  prompt. Example: Big Mom is a Cabin Mate swordsman because she's famous overall.
- Anime-only characters have fewer links, so they skew rare.
- "Captain" is meant to work like Krillion's "Too Clever" (the go-to "obscure" pick that isn't),
  but that needs real player answers. For now it's just the second-most-linked group.
- The long-term fix is to record what players actually type and tier from that, keeping wiki
  links for answers nobody has typed yet. That needs a small backend (e.g., when hosted on Vercel).

---

## Files
- `update.bat` / `update.py`: the updater.
- `config/prompts.json`, `config/overrides.json`, `reviews/event-review.csv` (Keep column): the files you edit.
- `one-piece-trivia.html`: the playable game. Double-click to open in a browser.
- `site/`: the live website (index.html, og.png, favicon.png). Vercel's Root Directory.
- `exports/`: prompt summary and the full answer list with tiers.
- `data/parsed-wiki.json`: every wiki article with categories, infobox fields, aliases and link counts.
- `data/prompts.json`: the answer data the game uses.
- `source/template.html`: the game without its data. Rules (tiers, timer, islands, points) are at
  the top of its script.
- `source/scripts/`: parse.py (dump → parsed-wiki.json), build_prompts.py (→ prompts.json),
  build_page.py (→ the game).
