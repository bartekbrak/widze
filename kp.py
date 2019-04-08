#!/usr/bin/env python
"""
Polish TV stations listing scraper for my blind uncle.
"""
import datetime
import os
import re
import sys
from argparse import ArgumentParser
from collections import Counter
from pprint import pprint, pformat

import babel.dates
from email_to import email_to
from pyquery import PyQuery as pq
import colored_traceback
colored_traceback.add_hook()

BASE = 'https://www.teleman.pl'

def debug(title, color=32, *msg):
    if args.debug:
        print(f'\033[{color}m{title}\033[0m', *msg)


template = """<html><head><meta charset="utf-8"></head>
<body><pre>\n
{name}\n
{body}
</pre></body>
</html>"""

index_template = """
<html><head><meta charset="utf-8"></head><body>
{name}<br>
{body}
</pre></body></html>"""


def parse_day(name, url):
    info = {
        'name': name,
        'url': url,
        'days': 0,
        'lines': 0
    }
    body = ''
    try:
        debug('parse_day', 32, name, url)
        for day in range(args.days_ahead + 1):
            info['days'] += 1
            date = datetime.date.today() + datetime.timedelta(days=day)
            dated_url = f'{BASE}{url}?date={date:%Y-%m-%d}'
            debug('dated_url', 34, dated_url)
            info['dated_url'] = dated_url
            p = pq(dated_url, parser='html')
            maybe_today = '\nDzisiaj, ' if date == datetime.date.today() else '\n'
            body += maybe_today + babel.dates.format_date(date, format='full', locale='pl_PL').strip() + '\n'

            where = 'ul.stationItems > li'

            listing = p(where)

            debug('listing len', 35, len(listing))
            info['listing_len'] = len(listing)
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
                info['lines'] += 1
                body += line + '\n'
        return body, info
    except Exception as e:
        info['aborted'] = str(e)
        return body, info


def channel_names():
    stacje = pq('https://www.teleman.pl/program-tv/stacje', parser='html')
    kanaly = stacje('#stations-index > a')
    for kanal in kanaly:
        yield kanal.attrib['href'], kanal.text


def parse_args():
    p = ArgumentParser(__doc__)
    p.add_argument('-a', '--all', action='store_true', help='Parse all channels')
    p.add_argument('-c', '--channel-name')
    p.add_argument('-C', '--channel-url')
    p.add_argument('-d', '--days-ahead', help='How many days ahead to parse', default=3)
    p.add_argument('-D', '--debug', action='store_true', help='print debug info as you go')
    p.add_argument('-e', '--email', action='store_true', help='Send report email.')
    p.add_argument('-A', '--admin-email', default='bartek.rychlicki@gmail.com')
    p.add_argument('--smtp-port', default=25, type=int)
    p.add_argument('--smtp-host', default='smtp.mailgun.org')
    p.add_argument('--smtp-user', default='postmaster@mg.brak.me')
    p.add_argument('--smtp-pass')
    global args
    args = p.parse_args()
    pprint(args.__dict__)
    assert not (args.all and args.channel_name), 'either all or channel'
    assert args.all or args.channel_name, 'either all or channel'
    if args.email:
        assert args.smtp_pass, 'smtp pass required'
    if args.channel_name:
        assert args.channel_url

if __name__ == '__main__':
    paren_dir = os.path.realpath(os.path.join(__file__, '..'))
    parse_args()
    c = Counter()

    if args.email:
        server = email_to.EmailServer(
            args.smtp_host,
            args.smtp_port,
            args.smtp_user,
            args.smtp_pass,
        )
        message = server.message()
        message.add('<pre>')
    if args.all:
        index = ''
        for url, name in channel_names():
            c['counter'] += 1
            with open(f'{paren_dir}/out/{name}.html', 'w') as f:
                body, info = parse_day(name, url)
                if 'aborted' in info:
                    c['aborted'] += 1
                if args.email:
                    message.add(pformat(info))
                f.write(template.format(name=name, body=body))
                index += f'<a href="{name}.html">{name}</a>\n<br>'
        with open(f'{paren_dir}/out/index.html', 'w') as f:
            f.write(index_template.format(name='index', body=index))
            debug('index written')

    elif args.channel_name:
        with open(f'{paren_dir}/out/{args.channel_name}.html', 'w') as f:
            body, info = parse_day(args.channel_name, args.channel_url)
            if args.email:
                message.add(pformat(info))
            f.write(template.format(name=args.channel_name, body=body))

    if args.email:
        debug('will send email now')
        c['date'] = datetime.date.today()
        message.add(pformat(c))
        message.add('</pre>')
        message.send(args.admin_email, f'{datetime.date.today()} report')
