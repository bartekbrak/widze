#!/usr/bin/env python
"""
Polish TV stations listing scraper for my blind uncle.
"""
import datetime
import re
from argparse import ArgumentParser

import babel.dates
from pyquery import PyQuery as pq
import colored_traceback
colored_traceback.add_hook()

BASE = 'https://www.teleman.pl'

def debug(title, color=32, *msg):
    if args.debug:
        print(f'\033[{color}m{title}\033[0m', *msg)


template = """
<html><head><meta charset="utf-8"></head><body><pre>\n
{name}\n
{body}
</pre></body></html>
"""

def parse_day(name, url):
    debug('parse_day', 32, name, url)
    for day in range(args.days_ahead + 1):
        date = datetime.date.today() + datetime.timedelta(days=day)
        dated_url = f'{BASE}{url}?date={date:%Y-%m-%d}'
        debug('dated_url', 34, dated_url)
        p = pq(dated_url, parser='html')
        maybe_today = '\nDzisiaj, ' if date == datetime.date.today() else '\n'
        yield maybe_today + babel.dates.format_date(date, format='full', locale='pl_PL').strip()

        where = 'ul.stationItems > li'

        listing = p(where)

        debug('listing len', 35, len(listing))

        for item in listing:
            if item.attrib['class'] == 'ad':
                continue
            godzina = pq(item.find('em')).text()
            if len(godzina) == 0:
                continue
            typ = pq(item)('p.genre').text()
            if typ is None:
                typ = ''
            tytul = pq(item)('a').text()

            # przetłumacz nawiasy: (1/2) na odcinek 1 z 2
            tytul = re.sub(r' \((\d+)/(\d+)\)', r'. odcinek \1 z \2', tytul)
            tytul = re.sub(r' \((\d+)\)', r'. odcinek \1', tytul)

            line = '%4s. %s. %s' % (
                godzina.zfill(5),
                typ,
                tytul
            )
            yield line

def channel_names():
    stacje = pq('https://www.teleman.pl/program-tv/stacje', parser='html')
    kanaly = stacje('#stations-index > a')
    for kanal in kanaly:
        yield kanal.attrib['href'], kanal.text


def parse_args():
    p = ArgumentParser(__doc__)
    p.add_argument('-a', '--all', action='store_true', help='Parse all channels')
    # p.add_argument('channel', required=False)
    p.add_argument('-d', '--days-ahead', help='How many days ahead to parse', default=3)
    p.add_argument('-D', '--debug', action='store_true', help='print debug info as you go')
    return p.parse_args()

if __name__ == '__main__':
    global args
    args = parse_args()
    if args.all:
        for url, name in channel_names():
            with open(f'out/{name}.html', 'w') as f:
                body = '\n'.join(parse_day(name, url))
                f.write(template.format(name=name, body=body))



