#!/usr/bin/env python
"""

mobiinfo.pl API.

http://cms.mobiinfo.pl/m/r7xp.php?IDKlienta=KONIN_MZK_NOWY&cmd=rozID&ID=160-01&IDLinii=54
"""
import datetime
import json
import sys
from argparse import ArgumentParser
from enum import Enum
from json import dumps
from typing import Tuple, Any
from urllib.parse import unquote, urlparse, parse_qsl, urlencode, ParseResult
import pandas as pd
from pydantic import BaseModel, validate_model

# utils

def add_url_params(url, params):
    """ Add GET params to provided URL being aware of existing.

    :param url: string of target URL
    :param params: dict containing requested params to be added
    :return: string with updated URL

    >> url = 'http://stackoverflow.com/test?answers=true'
    >> new_params = {'answers': False, 'data': ['some','values']}
    >> add_url_params(url, new_params)
    'http://stackoverflow.com/test?data=some&data=values&answers=false'
    """
    # Unquoting URL first so we don't loose existing args
    url = unquote(url)
    # Extracting url info
    parsed_url = urlparse(url)
    # Extracting URL arguments from parsed URL
    get_args = parsed_url.query
    # Converting URL arguments to dict
    parsed_get_args = dict(parse_qsl(get_args))
    # Merging URL arguments dict with new params
    parsed_get_args.update(params)

    # Bool and Dict values should be converted to json-friendly values
    # you may throw this part away if you don't like it :)
    parsed_get_args.update(
        {k: dumps(v) for k, v in parsed_get_args.items()
         if isinstance(v, (bool, dict))}
    )

    # Converting URL argument to proper query string
    encoded_get_args = urlencode(parsed_get_args, doseq=True)
    # Creating new parsed result object based on provided with new
    # URL arguments. Same thing happens inside of urlparse.
    new_url = ParseResult(
        parsed_url.scheme, parsed_url.netloc, parsed_url.path,
        parsed_url.params, encoded_get_args, parsed_url.fragment
    ).geturl()

    return new_url

# enums

class Konin(Enum):
    CHOPINA1 = '331-01'
    CHOPINA_CENTRUM = '331-02'
    PADEREWSKIEGO_SZYMANOWSKIEGO__PILSUDSKIEGO = '336-01'

def parse_args(args):
    p = ArgumentParser(__doc__)
    p.add_argument('ID')
    p.add_argument('IDLinii')
    p.add_argument('--IDKlienta', default='KONIN_MZK_NOWY')
    p.add_argument('--cmd', default='rozID')
    p.add_argument('--base-url', default='http://cms.mobiinfo.pl/m/r7xp.php')
    return p.parse_args(args)

def get_url(base_url, ID, IDLinii, IDKlienta, cmd):
    return add_url_params(base_url, {'ID': ID, 'IDLinii': IDLinii, 'IDKlienta': IDKlienta, 'cmd': cmd, })


class Meta(BaseModel):
    other_lines: Tuple[int, ...]
    stop_name: str
    valid_since: datetime.date
    destination_stop: str
    stops: Tuple[str, ...]

    def __init__(self, raise_exc=False, **data: Any) -> None:
        values, fields_set, errors = validate_model(self, data, raise_exc=raise_exc)
        object.__setattr__(self, '__values__', values)
        object.__setattr__(self, '__fields_set__', fields_set)


def get_meta(df):
    return Meta(
        raise_exc        = True,
        other_lines      = tuple(map(int, df[1].iloc[0].dropna())),
        stop_name        = df[2][0][0].split()[1],  # df[4][2][0].split()[1]
        valid_since      = df[4][3][0].split()[2],
        destination_stop = df[4][2][1].split()[1],
        # TODO: lol
        stops            = tuple(df[8][1][1:]) if len(df) > 8 else tuple(df[7][1][1:]),
    )

def timetable(df):
    for t in zip(df[6][0][2:], df[6][1][2:]):
        for minutes in t[1].split(' '):
            minutes = minutes.replace('.', '')
            yield int(t[0]), minutes


def as_html(df: pd.DataFrame, outfile: str):
    with open(outfile, 'w') as f:
        meta = get_meta(df)
        f.write(f'<html><head><meta charset="utf-8"></head><body><pre>\n')
        f.write(f'Przystanek {meta.stop_name}. Kierunek {meta.destination_stop}\n')
        for h, m in timetable(df):
            f.write(f'{h}:{m}\n')
        f.write('</pre></body></html>')


def for_andrzej():
    for line in ('54', '55', '59'):
        url = get_url(**parse_args((Konin.CHOPINA_CENTRUM.value, line)).__dict__)
        as_html(pd.read_html(url), f'{line}.{Konin.CHOPINA_CENTRUM.name}.html')
    url = get_url(**parse_args((Konin.PADEREWSKIEGO_SZYMANOWSKIEGO__PILSUDSKIEGO.value, '53')).__dict__)
    as_html(pd.read_html(url), f'53.{Konin.PADEREWSKIEGO_SZYMANOWSKIEGO__PILSUDSKIEGO.name}.html')


if __name__ == '__main__':
    for_andrzej()
    # args = parse_args(sys.argv[1:])
    # url = get_url(**args.__dict__)
    # x = timetable(url)


def test_times():

    cases = (
        ((Konin.CHOPINA1.value, '54'), 'Zakładowa-końcowy.'        , ((5, '34') , (6, '06') , (6, '41') , (7, '11') , (7 , '41') , (8 , '11') , (8 , '41') , (9 , '19') , (9 , '59') , (10, '39')  , (11, '19') , (11, '59') , (12, '39') , (13, '11') , (13, '41')   , (14, '11')  , (14, '41') , (15, '11') , (15, '41') , (16, '11') , (16, '41') , (17, '11') , (18, '05') , (19, '05') , (20, '04'), (21, '04'))),
        ((Konin.CHOPINA_CENTRUM.value, '54'), 'Nowe-Brzeźno-końcowy.'     , ((5, '16a'), (5, '46a'), (6, '18b'), (6, '58a'), (7 , '18a'), (7 , '48a'), (8 , '18a'), (8 , '50a'), (9 , '30a'), (10, '10a') , (10, '50a'), (11, '30a'), (12, '10a'), (12, '48a'), (13, '18a')  , (13, '48b') , (14, '18a'), (14, '48a'), (15, '18a'), (15, '48a'), (16, '18a'), (16, '58a'), (17, '58a'), (18, '58a'), (19, '-') , (20, '01a') , (20, '59a'), (21, '59a'))),
        ((Konin.CHOPINA1.value, '55'), 'Janowska-końcowy.'         , ((4, '23#'), (5, '10h'), (6, '06h'), (7, '-')  , (8 , '26h'), (9 , '-')  , (10, '26') , (11, '-')  , (12, '06') , (13, '11ah'), (14, '27h'), (15, '27a'), (17, '11') , (19, '11') , (21, '10h'))),
        ((Konin.CHOPINA_CENTRUM.value, '55'), 'Piłsudskiego-końcowy.'     , ((5, '25') , (6, '46') , (7, '24') , (8, '42') , (9 , '42') , (10, '-')  , (11, '42') , (12, '-')  , (13, '26') , (14, '46')  , (15, '46') , (16, '46') , (18, '31') , (20, '28') , (22, '43'))) ,
        ((Konin.CHOPINA1.value, '59'), 'Zakładowa-końcowy.'        , ((6, '36') , (7, '26') , (8, '26') , (9, '39') , (10, '59') , (11, '-')  , (12, '19') , (13, '26') , (14, '26') , (15, '26')  , (16, '26') , (17, '41') , (18, '40') , (19, '40') , (20, '39')   , (21, '39'))),
        ((Konin.CHOPINA_CENTRUM.value, '59'), 'Staromorzysławska-końcowy.', ((6, '33') , (7, '33') , (8, '33') , (9, '50') , (10, '-')  , (11, '10') , (12, '30') , (13, '33') , (14, '33') , (15, '33')  , (16, '33') , (17, '28') , (18, '28') , (19, '28') , (20, '29')   , (21, '29'))),
    )
    for (stop, line), destination, expected in cases:
        args = parse_args((stop, line))
        url = get_url(**args.__dict__)
        df = pd.read_html(url)
        meta = get_meta(df)
        times = tuple(timetable(df))
        assert tuple(times) == expected
        assert meta.destination_stop == destination
