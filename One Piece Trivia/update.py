r"""Update One Piece Trivia.

  python update.py path\to\onepiece_pages_current_xml.7z   (new wiki dump: re-parse everything)
  python update.py path\to\onepiece_pages_current.xml      (same, already extracted)
  python update.py                                         (no dump: just re-apply config and overrides)

Or drag a dump file onto update.bat. Rebuilds data/prompts.json, the two CSV
exports, and one-piece-trivia.html.
"""
import csv, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'source' / 'scripts'))
from parse import parse                      # noqa: E402
from build_prompts import build, TIER_NAMES  # noqa: E402
from build_page import build_page, build_site  # noqa: E402

PARSED = ROOT / 'data' / 'parsed-wiki.json'
PROMPTS = ROOT / 'data' / 'prompts.json'
POINTS = [10, 15, 30, 60, 85, 100]
# Your live site's address, once Vercel gives you one (e.g. 'https://one-piece-trivia.vercel.app').
# Used for link previews in group chats; the site works without it.
SITE_URL = ''


def extract_7z(archive, dest):
    try:
        import py7zr
    except ImportError:
        py7zr = None
    if py7zr:
        with py7zr.SevenZipFile(archive) as z:
            z.extractall(dest)
    else:
        exe = shutil.which('7z') or next((p for p in [r'C:\Program Files\7-Zip\7z.exe', r'C:\Program Files (x86)\7-Zip\7z.exe'] if os.path.exists(p)), None)
        if not exe:
            sys.exit('Can\'t open .7z files yet. Run:  python -m pip install py7zr   (or extract the dump with 7-Zip and pass the .xml).')
        subprocess.run([exe, 'x', '-y', '-o' + str(dest), str(archive)], check=True, stdout=subprocess.DEVNULL)
    xmls = list(Path(dest).rglob('*.xml'))
    if not xmls:
        sys.exit('No .xml file found inside the archive.')
    return max(xmls, key=lambda p: p.stat().st_size)


def export_csvs(data):
    (ROOT / 'exports').mkdir(exist_ok=True)
    with open(ROOT / 'exports' / 'one-piece-trivia-prompts.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['Prompt', 'Answers', 'Anime-only', 'Pirate King answer', 'Cabin Mate examples', 'Yonko examples'])
        for p in data:
            a = p['a']
            w.writerow([p['p'], len(a), sum(x['nc'] for x in a), next((x['n'] for x in a if x['t'] == 5), ''),
                        ', '.join([x['n'] for x in a if x['t'] == 0][:5]),
                        ', '.join([x['n'] for x in a if x['t'] == 4 and not x['nc']][:5])])
    with open(ROOT / 'exports' / 'one-piece-trivia-all-answers.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['Prompt', 'Answer', 'Tier', 'Points', 'Anime-only'])
        for p in data:
            for x in sorted(p['a'], key=lambda x: -x['t']):
                w.writerow([p['p'], x['n'], TIER_NAMES[x['t']], POINTS[x['t']], 'yes' if x['nc'] else ''])


def main():
    dump = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].strip() else None
    if dump:
        if not dump.exists():
            sys.exit(f'File not found: {dump}')
        print(f'1/4  Reading wiki dump {dump.name} (a few minutes)...')
        with tempfile.TemporaryDirectory() as tmp:
            xml = extract_7z(dump, tmp) if dump.suffix.lower() == '.7z' else dump
            parse(str(xml), str(PARSED), log=lambda m: print('     ' + m))
    elif not PARSED.exists():
        sys.exit('No wiki data yet. Pass a dump file: python update.py onepiece_pages_current_xml.7z')
    else:
        print('1/4  No dump given, reusing data/parsed-wiki.json')
    print('2/4  Building answer lists...')
    data = build(str(PARSED), str(ROOT / 'config' / 'prompts.json'), str(ROOT / 'config' / 'overrides.json'), str(PROMPTS),
                 review_path=str(ROOT / 'reviews' / 'event-review.csv'))
    print('3/4  Writing CSV exports...')
    export_csvs(data)
    print('4/4  Building one-piece-trivia.html and site/index.html...')
    build_page(str(ROOT / 'source' / 'template.html'), str(PROMPTS), str(ROOT / 'one-piece-trivia.html'))
    (ROOT / 'site').mkdir(exist_ok=True)
    build_site(str(ROOT / 'one-piece-trivia.html'), str(ROOT / 'site' / 'index.html'), SITE_URL)
    print('Done. Open one-piece-trivia.html to play the updated game.')
    print('To update the live site: commit and push in GitHub Desktop. Vercel redeploys in about 30 seconds.')


if __name__ == '__main__':
    main()
