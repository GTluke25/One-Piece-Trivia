"""Parse a One Piece Wiki XML dump into parsed-wiki.json.

Collects, for every article: categories, infobox type and fields, redirect aliases,
and inbound links (how many other articles link to it), which is the rarity signal.
Also collects which characters appear in each manga chapter (with the group they're
listed under), each story arc's chapter range, and the links inside event articles.
These power the "who was at <event>" prompts.
"""
import collections, json, re, sys
import xml.etree.ElementTree as ET

CAT_RE = re.compile(r'\[\[\s*Category\s*:\s*([^\]|]+)', re.I)
LINK_RE = re.compile(r'\[\[([^\]|#]+)')
REDIR_RE = re.compile(r'#REDIRECT\s*\[\[([^\]|#]+)', re.I)
TMPL_RE = re.compile(r'\{\{\s*([^|}\n]+)')
FIELD_RE = re.compile(r'^\|\s*([a-zA-Z0-9 _]+?)\s*=\s*(.*)$', re.M)
CHAPTER_RE = re.compile(r'Chapter (\d+)')
RANGE_RE = re.compile(r'\|([^=|\n]+?)=\s*\{\{#switch:\{\{\{2\}\}\}\|st=(\d+)\|end=(\d+)')
# Chapter appearances that don't mean the character was physically there
NOT_PRESENT = re.compile(r'\((?:[^)]*\b(?:cover|flashback|mentioned|silhouette|picture|portrait|photo|poster|dream|'
                         r'imagination|imagined|vivre card|newspaper|fantasy|statue|illustration)\b)', re.I)


def infobox_fields(seg):
    """'|key = value' lines from an infobox; a value may continue over several lines."""
    fields, cur = {}, None
    for line in seg.split('\n'):
        m = re.match(r'^\|\s*([a-zA-Z0-9 _]+?)\s*=\s*(.*)$', line)
        if m:
            cur = m.group(1).strip().lower()
            if cur in fields:
                cur = None  # keep the first occurrence
            else:
                fields[cur] = m.group(2).strip()
        elif line.startswith('}}') or line.startswith('|'):
            if line.startswith('}}'):
                break
            cur = None
        elif cur:
            fields[cur] += ' ' + line.strip()
    return {k: v[:2000] for k, v in fields.items()}


def norm(t):
    t = t.strip().replace('_', ' ')
    return t[:1].upper() + t[1:] if t else t


def chapter_cast(text):
    """[(character, group heading)] from a chapter page's Characters table."""
    i = text.find('===Characters===')
    if i < 0:
        return []
    seg = text[i:]
    j = seg.find('\n==', 5)
    seg = seg[:j] if j > 0 else seg
    out, head = [], ''
    for line in seg.split('\n'):
        if line.startswith('|') or line.startswith('----'):
            head = ''
        if line.startswith(';'):
            head = re.sub(r'\[\[([^\]|]+)(\|[^\]]*)?\]\]', r'\1', line.lstrip(';')).strip()
        if NOT_PRESENT.search(line):
            continue
        for l in re.findall(r'^\*+\s*\[\[([^\]|#]+)', line):
            out.append([norm(l), head])
    return out


def parse(xml_path, out_path, log=print):
    articles, redirects, tabs = {}, {}, {}
    chapters, arc_ranges, event_links = {}, {}, {}
    inlinks, cat_counts = collections.Counter(), collections.Counter()
    ns_tag = None
    for _, el in ET.iterparse(xml_path, events=('end',)):
        if not el.tag.endswith('}page'):
            continue
        ns_tag = ns_tag or el.tag[:-len('page')]
        ns = el.findtext(ns_tag + 'ns')
        title = el.findtext(ns_tag + 'title')
        if ns == '10':
            text = el.findtext(f'{ns_tag}revision/{ns_tag}text') or ''
            if title.endswith(' Tabs Top'):
                # Major characters keep their infobox on "Template:<Name> Tabs Top"
                bi = re.search(r'\{\{\s*Char Box', text)
                if bi:
                    fields = infobox_fields(text[bi.start(): bi.start() + 12000])
                    tabs[norm(fields.get('root') or title[len('Template:'):-len(' Tabs Top')])] = fields
            elif title == 'Template:Range/Chapter':
                for m in RANGE_RE.finditer(text):
                    arc_ranges[m.group(1).strip()] = [int(m.group(2)), int(m.group(3))]
            el.clear(); continue
        if ns != '0':
            el.clear(); continue
        text = el.findtext(f'{ns_tag}revision/{ns_tag}text') or ''
        m = REDIR_RE.match(text.lstrip())
        if m:
            redirects[title] = norm(m.group(1))
        else:
            cats = sorted({norm(c) for c in CAT_RE.findall(text)})
            cat_counts.update(cats)
            links = {norm(l) for l in LINK_RE.findall(text) if ':' not in l}
            inlinks.update(links)
            box = next((norm(t) for t in TMPL_RE.findall(text) if 'box' in t.lower()), None)
            fields = {}
            if box:
                bi = re.search(r'\{\{\s*' + re.escape(box.split()[0]), text, re.I)
                fields = infobox_fields(text[bi.start(): bi.start() + 12000]) if bi else {}
            articles[title] = {'len': len(text), 'cats': cats, 'box': box, 'fields': fields}
            if box == 'Event Box':
                event_links[title] = sorted(links)
            cm = CHAPTER_RE.fullmatch(title)
            if cm:
                chapters[int(cm.group(1))] = chapter_cast(text)
        el.clear()

    for root, fields in tabs.items():
        a = articles.get(redirects.get(root, root))
        if a:
            a['fields'] = {**fields, **a['fields']}
            a['box'] = 'Char Box'
    resolved = collections.Counter()
    for t, n in inlinks.items():
        resolved[redirects.get(t, t)] += n
    for t, a in articles.items():
        a['inlinks'] = resolved.get(t, 0)
        a['aliases'] = []
    for r, tgt in redirects.items():
        if tgt in articles:
            articles[tgt]['aliases'].append(r)
    # point chapter casts and event links at real page names, not redirects
    for n, cast in chapters.items():
        chapters[n] = [[redirects.get(c, c), h] for c, h in cast]
    for e, links in event_links.items():
        event_links[e] = sorted({redirects.get(l, l) for l in links})

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'articles': articles, 'cat_counts': cat_counts.most_common(), 'chapters': chapters,
                   'arc_ranges': arc_ranges, 'event_links': event_links}, f)
    log(f'Parsed {len(articles)} articles, {len(redirects)} redirects, {len(tabs)} character tab infoboxes, '
        f'{len(chapters)} chapters, {len(arc_ranges)} arc ranges, {len(event_links)} events.')


if __name__ == '__main__':
    parse(sys.argv[1], sys.argv[2])
