"""Build the playable game file, and the live-site version of it.

build_page: template + answer data -> one-piece-trivia.html (open locally / Claude artifact)
build_site: one-piece-trivia.html -> site/index.html, a complete web page with link-preview
            tags, ready for Vercel. The site/ folder also holds favicon.png and og.png.
"""
import sys

DESCRIPTION = 'Name the rarest One Piece answers you can. Raise your bounty, outrun the Marines, reach Elbaf.'


def build_page(template_path, data_path, out_path):
    t = open(template_path, encoding='utf-8').read()
    d = open(data_path, encoding='utf-8').read().replace('</', '<\\/')
    open(out_path, 'w', encoding='utf-8').write(t.replace('__DATA__', d))


def build_site(game_path, out_path, site_url=''):
    game = open(game_path, encoding='utf-8').read()
    cut = game.index('</style>') + len('</style>')
    head, body = game[:cut], game[cut:]
    head = head.replace('<meta charset="utf-8">\n', '')
    base = site_url.rstrip('/')
    image = f'{base}/og.png' if base else '/og.png'
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{DESCRIPTION}">
<meta property="og:type" content="website">
<meta property="og:title" content="One Piece Trivia">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:image" content="{image}">
{f'<meta property="og:url" content="{base}/">' if base else ''}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="/favicon.png">
<style>html, body {{ margin: 0; }}</style>
{head}
</head>
<body>
{body}
</body>
</html>
'''
    open(out_path, 'w', encoding='utf-8').write(page)


if __name__ == '__main__':
    build_page(*sys.argv[1:4])
