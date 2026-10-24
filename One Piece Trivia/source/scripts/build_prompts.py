"""Build the game's answer data (prompts.json) from parsed-wiki.json.

Prompts come from config/prompts.json. Your manual choices in config/overrides.json
(and your Keep column in reviews/event-review.csv) are applied last, so a wiki update
never erases them.
"""
import csv, json, os, re, sys, collections

TIER_NAMES = ['Cabin Mate', 'Captain', 'Rookies', 'Supernova', 'Yonko', 'Pirate King']
# Share of each prompt's answers (most-linked first) that land in each tier.
# 0-8% Cabin Mate, 8-20% Captain, 20-45% Rookies, 45-75% Supernova, 75-100% Yonko.
CUTS = [0.08, 0.20, 0.45, 0.75]
PIRATE_KING, YONKO = 5, 4
REVIEW_COLS = ['Prompt', 'Character', 'Evidence', 'Chapters seen in', 'Listed under', 'Keep']
EVIDENCE_HELP = {
    'Confirmed': 'linked from the event article',
    'Likely': 'listed under a group that took part',
    'Questionable': 'only seen in the chapters; may be a cutaway',
}


def norm(t):
    t = t.strip().replace('_', ' ')
    return t[:1].upper() + t[1:] if t else t


def strip_refs(v):
    v = re.sub(r'\{\{\s*Qref[^{}]*(\{\{[^{}]*\}\}[^{}]*)*\}\}', '', v)
    return re.sub(r'<ref[^>]*>.*?</ref>|<ref[^>]*/>', '', v)


def key(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def display(t):
    # 'Art of Weather/Clima-Tact' -> 'Clima-Tact'; 'Emma (Non-Canon)' -> 'Emma'
    return re.sub(r'\s*\([^)]*\)$', '', t.split('/')[-1])


def links_in(v):
    return {norm(m) for m in re.findall(r'\[\[([^\]|#]+)', strip_refs(v))}


def epithets(a):
    out = []
    for q in re.findall(r'"([^"]{3,60})"', a['fields'].get('epithet', '')):
        q = re.sub(r"<[^>]+>|''|\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r'\1', q).strip()
        q = re.sub(r'^The\s+', '', q)
        if q and not re.search(r'[぀-ヿ一-鿿]', q):
            out.append(q)
    return out


def letter_names(t, a, letter, use_epithets):
    """Names of a character that start with `letter`: full name, single name parts
    (so 'Luffy' counts for L), multi-word aliases and, optionally, epithets.
    One-word redirects are skipped because many are misspellings ('Ruffy')."""
    full = display(t)
    cands = {full} | {w for w in re.split(r'\s+', full) if len(w) >= 3 and not w.endswith('.')}
    cands |= {al for al in a['aliases'] if ' ' in al.strip()}
    if use_epithets:
        cands |= set(epithets(a))
    return {c for c in cands if c[:1].upper() == letter.upper()}


def read_review(path):
    keep = {}
    if path and os.path.exists(path):
        for enc in ('utf-8-sig', 'cp1252'):
            try:
                with open(path, newline='', encoding=enc) as f:
                    for row in csv.DictReader(f):
                        v = (row.get('Keep') or '').strip().lower()
                        if v in ('yes', 'no', 'y', 'n'):
                            keep[(row['Prompt'], row['Character'])] = v[0] == 'y'
                break
            except UnicodeDecodeError:
                keep = {}
    return keep


def build(parsed_path, prompts_cfg_path, overrides_path, out_path, review_path=None, log=print):
    D = json.load(open(parsed_path, encoding='utf-8'))
    A = D['articles']
    cfg = json.load(open(prompts_cfg_path, encoding='utf-8'))['prompts']
    ov = json.load(open(overrides_path, encoding='utf-8'))
    twins = {c[len('Non-Canon '):] for c, _ in D['cat_counts'] if c.startswith('Non-Canon ')}
    chapters = {int(k): v for k, v in D.get('chapters', {}).items()}
    reviewed = read_review(review_path)
    review_rows = []

    def anime_only(a):
        # Has a Non-Canon category, and no canon category that has a Non-Canon twin.
        if not any(c.startswith('Non-Canon') for c in a['cats']):
            return False
        return not any(not c.startswith('Non-Canon') and c in twins for c in a['cats'])

    def is_char(a):
        return a['box'] == 'Char Box'

    def presence(p):
        """Characters seen in the event's chapters, sorted into Confirmed / Likely / Questionable."""
        q, ev = p['prompt'], p.get('event')
        rng = p.get('chapters') or D['arc_ranges'].get(p.get('arc', ''))
        if not rng:
            warnings.append(f'[{q}] no chapter range: add "chapters": [first, last] or a valid "arc"'); return set()
        f = A.get(ev, {}).get('fields', {}) if ev else {}
        groups = set()
        for k in ('factions', 'commanders', 'other', 'instigator'):
            groups |= links_in(f.get(k, ''))
        groups |= {norm(g) for g in p.get('groups', [])}
        art = set(D['event_links'].get(ev, [])) if ev else set()
        group_re = re.compile('|'.join(re.escape(g) for g in sorted(groups)) +
                              r'|Marine|Admiral|Ensign|Seaman|Commodore|Lieutenant|Warlord|Shichibukai|Pacifista', re.I)
        seen, heads = collections.Counter(), collections.defaultdict(set)
        for n in range(rng[0], rng[1] + 1):
            for c, h in chapters.get(n, []):
                if c in A and is_char(A[c]):
                    seen[c] += 1
                    if h: heads[c].add(h)
        kept = set()
        for c in seen:
            evid = 'Confirmed' if c in art else 'Likely' if any(group_re.search(h) for h in heads[c]) else 'Questionable'
            # Keep: your yes/no from the review sheet; otherwise yes, except Questionable ("?" = not reviewed, left out)
            decided = reviewed.get((q, display(c)))
            keep = decided if decided is not None else evid != 'Questionable'
            mark = ('yes' if keep else 'no') if decided is not None or evid != 'Questionable' else '?'
            review_rows.append([q, display(c), evid, seen[c], '; '.join(sorted(heads[c]))[:120], mark])
            if keep:
                kept.add(c)
        return kept

    def matcher(p):
        cats = set(p.get('categories', []))
        if p.get('include_anime_only', True):
            cats |= {'Non-Canon ' + c for c in cats}
        box = p.get('infobox')
        affs = {norm(x) for x in p.get('affiliations', [])}
        no_former = not p.get('include_former', True)
        df = (p.get('devil_fruit_type') or '').lower()
        letter = p.get('starts_with')
        present = presence(p) if (p.get('event') or p.get('arc') or p.get('chapters')) else None

        def match(t, a):
            if present is not None:
                return t in present
            if letter:
                return is_char(a) and bool(letter_names(t, a, letter, p.get('epithets', True)))
            if df and is_char(a):
                v = strip_refs(a['fields'].get('dftype', '')).lower()
                if (df == 'any' and (v or a['fields'].get('dfname'))) or (df != 'any' and df in v):
                    return True
            if box and a['box'] == box: return True
            if cats & set(a['cats']): return True
            if affs and is_char(a):  # crew membership only counts for characters
                hits = links_in(a['fields'].get('affiliation', '')) & affs
                if hits and no_former:
                    v = strip_refs(a['fields'].get('affiliation', ''))
                    hits = {h for h in hits if not re.search(r'\[\[' + re.escape(h) + r'(\|[^\]]*)?\]\]\s*\(former', v, re.I)}
                if hits: return True
            return False
        return match

    warnings, data = [], []
    for p in cfg:
        q = p['prompt']
        f = matcher(p)
        letter = p.get('starts_with')
        excl = set(ov.get('exclude', {}).get(q, []))
        rows = sorted(((a['inlinks'], t, a) for t, a in A.items()
                       if f(t, a) and display(t) not in excl and t not in excl
                       and (p.get('include_anime_only', True) or not anime_only(a))),
                      key=lambda r: -r[0])
        n = len(rows)
        if n < 15:
            warnings.append(f'[{q}] only {n} answers; tiers will be coarse')
        answers = []
        for i, (links, t, a) in enumerate(rows):
            if letter:
                names = letter_names(t, a, letter, p.get('epithets', True))
            else:
                names = {display(t), t} | set(a['aliases'])
                if a['box'] == 'Devil Fruit Box' and a['fields'].get('ename'):
                    for part in re.split(r';|<br\s*/?>', a['fields']['ename']):
                        part = re.sub(r'\([^)]*\)', '', part).strip()
                        if part:
                            names.add(part)
            answers.append({'n': display(t), 'names': names, 't': sum(i / n >= c for c in CUTS),
                            'nc': anime_only(a), 'l': links})
        by_name = {x['n'].lower(): x for x in answers}

        # Extra accepted spellings / nicknames
        for name, extra in ov.get('aliases', {}).get(q, {}).items():
            x = by_name.get(name.lower())
            if x: x['names'] |= set(extra)
            else: warnings.append(f'[{q}] alias target not found: {name}')
        # Manual tier changes
        for name, tier in ov.get('tiers', {}).get(q, {}).items():
            x = by_name.get(name.lower())
            if not x: warnings.append(f'[{q}] tier override not found: {name}'); continue
            if tier not in TIER_NAMES: warnings.append(f'[{q}] unknown tier "{tier}" for {name}'); continue
            x['t'] = TIER_NAMES.index(tier)
        # Pirate King: your pick if set, otherwise the most-linked canon Yonko answer
        pick = ov.get('pirate_king', {}).get(q)
        for x in answers:
            if x['t'] == PIRATE_KING and pick:
                x['t'] = YONKO
        if pick:
            x = by_name.get(pick.lower())
            if not x:
                warnings.append(f'[{q}] Pirate King pick not found: {pick} (using automatic pick)'); pick = None
            elif x['nc']:
                warnings.append(f'[{q}] Pirate King pick {pick} is anime-only, which can only reach Yonko (using automatic pick)'); pick = None
            else:
                x['t'] = PIRATE_KING
        # Anime-only answers can never be Pirate King
        for x in answers:
            if x['nc'] and x['t'] == PIRATE_KING:
                x['t'] = YONKO; warnings.append(f'[{q}] {x["n"]} is anime-only, so it was capped at Yonko')
        if not any(x['t'] == PIRATE_KING for x in answers):
            pool = [x for x in answers if x['t'] == YONKO and not x['nc']] or \
                   [x for x in answers if x['t'] == YONKO - 1 and not x['nc']]
            if pool: max(pool, key=lambda x: x['l'])['t'] = PIRATE_KING

        king = next((x['n'] for x in answers if x['t'] == PIRATE_KING), '-')
        log(f'  {q}: {n} answers, Pirate King = {king}{" (your pick)" if pick else ""}')
        data.append({'p': q, 'a': [{'n': x['n'], 'k': sorted({key(s) for s in x['names'] if len(key(s)) >= 3}),
                                    't': x['t'], 'nc': x['nc']} for x in answers]})

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'))
    if review_path:
        os.makedirs(os.path.dirname(review_path), exist_ok=True)
        order = {'Questionable': 0, 'Likely': 1, 'Confirmed': 2}
        review_rows.sort(key=lambda r: (r[0], order[r[2]], -r[3]))
        with open(review_path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(REVIEW_COLS)
            w.writerows(review_rows)
        todo = sum(1 for r in review_rows if r[5] == '?')
        if todo:
            log(f'  {todo} questionable event answers still need your review in reviews/event-review.csv')
    for w in warnings:
        log('  WARNING ' + w)
    return data


if __name__ == '__main__':
    build(*sys.argv[1:6])
