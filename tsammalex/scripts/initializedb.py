# coding: utf8
from __future__ import unicode_literals
import sys
import json
import re
from itertools import chain
from collections import defaultdict

from path import path
from clld.util import slug
from clld.scripts.util import initializedb, Data, bibtex2source, glottocodes_by_isocode
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib.dsv import reader

import tsammalex
from tsammalex import models
from tsammalex.scripts import wiki
from tsammalex.scripts.refs import get_refs
from tsammalex.scripts.word_data import parsed_word, parsed_words


files_dir = path('/home/robert/venvs/clld/tsammalex/data/files')
year_pages = re.compile('\([0-9]{4}:(?P<pages>[0-9]+)\)')

#
# TODO: fix plantzafrica links! they only go to the frameset!
#
LANGUAGES = {
    'Afrikaans': {'ISO 639-3': 'afr', 'geo': (-30.8, 21.0)},
    'Deutsch': {'ISO 639-3': 'deu'},
    'Gǀui': {'ISO 639-3': 'gwj', 'geo': (-23.5, 23.6)},
    u"Ju\u01c0'hoansi": {'ISO 639-3': 'ktz', 'geo': (-20.1, 20.4)},
    'Khoekhoegowab': {'ISO 639-3': 'naq', 'geo': (-26.0, 18.0), 'Dialects': {
        'N': 'Nama',
        'D': 'Damara',
        'HM': 'Haiǁom',
        'ǂA': 'ǂĀkhoe'},  # (cf. Haacke & Eiseb 2002:viii-ix).
    },
    'Khwedam': {'ISO 639-3': 'xuu', 'geo': (-17.9, 22.7)},
    'Naro': {'ISO 639-3': 'nhr', 'geo': (-22.3, 21.0)},
    'Nǀuu': {'ISO 639-3': 'ngh', 'geo': (-28.3, 21.3), 'Dialects': {
        'W': 'Western Nǀuu',
        'E': 'Eastern Nǀuu'}},
    'Oshiwambo': {'ISO 639-3': 'kua', 'geo': (-17.7, 15.7)},  # [1]
    'Otjiherero': {'ISO 639-3': 'her', 'geo': (-21.7, 18.1)},
    'Setswana': {'ISO 639-3': 'tsn', 'geo': (-25.7, 25.45)},
    'Shekgalagadi': {'ISO 639-3': 'xkv', 'geo': (-24.1, 23.0)},

    'Taa': {'ISO 639-3': 'nmn', 'geo': (-23.7, 21.1)#, 'Dialects': {

        #'W': 'West ǃXoon (West Taa: near Corridor 13, Namibia)',
        #'N': "'Nǀoha - Ngwatle varieties ('ǃAma', western varieties of East Taa: near "
        #     "Corridor 13/Namibia to Ukwi, Ngwatle, Zutshwa, and probably Monong, Make, "
        #     "and Lehututu/Botswana)",
        #'E': "East ǃXoon (northern varieties of East Taa: Lone Tree, Kacgae, Bere, and "
        #     "probably Hunhukwe/Botswana)",
        #'C': "Tshaasi (central varieties of East Taa: Kang, Maretswaane, Inalegolo, and "
        #     "probably Khekhenye, Kanaku, and Khokhotsha)",
        #'S': "ǂHuan (Southern varieties of East Taa: Inalegolo and Khokhotsha/Botswana)"},
        # Numbers in parentheses refer to noun classes (singular/plural).
        # The orthographical representation is the one suggested by the DoBeS project.

    },

    'ǃXun': {'ISO 639-3': 'knw', 'geo': (-18.2, 19.1)},
    'ǂHoan': {'ISO 639-3': 'huc', 'geo': (-23.8, 24.7), 'name': "ǂ'Amkoe"},
    'IsiZulu': {'ISO 639-3': 'zul', 'geo': (-28.5, 30.6)},

    'Taa/Tshaasi': {'ISO 639-3': 'nmn-t', 'geo': (-23.8, 22.7), 'description': "central varieties of East Taa: Kang, Maretswaane, Inalegolo, and probably Khekhenye, Kanaku, and Khokhotsha"},
    'Taa/East ǃXoon': {'ISO 639-3': 'nmn-e', 'geo': (-22.8, 21.9), 'description': "northern varieties of East Taa: Lone Tree, Kacgae, Bere, and probably Hunhukwe/Botswana"},
    'Taa/ǃAma': {'ISO 639-3': 'nmn-a', 'geo': (-23.7, 20.9), 'description': "'ǃAma', western varieties of East Taa: near Corridor 13/Namibia to Ukwi, Ngwatle, Zutshwa, and probably Monong, Make, and Lehututu/Botswana"},
    'Taa/ǂHuan': {'ISO 639-3': 'nmn-h', 'geo': (-24.3, 22.9), 'description': "Southern varieties of East Taa: Inalegolo and Khokhotsha/Botswana"},
    'Taa/West ǃXoon': {'ISO 639-3': 'nmn-w', 'geo': (-23.7, 19.9), 'description': "West Taa: near Corridor 13, Namibia"},
}

COUNTRIES = {
    'angola': ('Angola', 'AO'),
    'botswana': ('Botswana', 'BW'),
    'southafrica': ('South Africa', 'ZA'),
    'zimbabwe': ('Zimbabwe', 'ZW'),
    'namibia': ('Namibia', 'NA'),
    'mozambique': ('Mozambique', 'MZ'),
}


def get_metadata():
    data = Data()
    dataset = common.Dataset(
        id="tsammalex",
        name="Tsammalex",
        description="A lexical database on plants and animals (preliminary version)",
        publisher_name="Max Planck Institute for Evolutionary Anthropology",
        publisher_place="Leipzig",
        publisher_url="http://www.eva.mpg.de",
        domain='tsammalex.clld.org',
        license='http://creativecommons.org/licenses/by/3.0/',
        contact='naumann@eva.mpg.de',
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 3.0 Unported License'})
    DBSession.add(dataset)

    for i, spec in enumerate([('naumann', "Christfried Naumann")]):
        DBSession.add(common.Editor(
            dataset=dataset,
            ord=i + 1,
            contributor=common.Contributor(id=spec[0], name=spec[1])))

    contrib = data.add(common.Contribution, 'tsammalex', name="Tsammalex", id="tsammalex")
    glottolog = glottocodes_by_isocode(
        'postgresql://robert@/glottolog3', cols='id latitude longitude'.split())
    return data, contrib, glottolog


def main(args):
    taa_variety_map = {
        'c': 'Taa/Tshaasi',
        'e': 'Taa/East ǃXoon',
        'n': 'Taa/ǃAma',
        's': 'Taa/ǂHuan',
        'w': 'Taa/West ǃXoon'}
    data, contrib, glottolog = get_metadata()

    wiki.get_categories(args)
    refs = wiki.get_refs(args)
    for rec in refs.records:
        data.add(models.Bibrec, rec.id, _obj=bibtex2source(rec, cls=models.Bibrec))

    for name, props in LANGUAGES.items():
        iso = props['ISO 639-3']
        if len(iso) == 3:
            gcode, lat, lon = glottolog[iso]
        lat, lon = props.get('geo', (None, None))
        lang = data.add(
            models.Languoid, name, id=iso, name=props.get(name, name), latitude=lat, longitude=lon)
        #
        # TODO: add glottocode!
        #
        for id_, name_ in props.get('Dialects', {}).items():
            desc = None
            if '(' in name_:
                name_, desc = name_.split('(', 1)
                name_ = name_.strip()
                desc = desc.split(')')[0].strip()
            id_ = '%s-%s' % (iso, slug(id_))
            data.add(
                models.Variety, id_, id=id_, name=name_, description=desc, language=lang)

    with open(args.data_file('species.json')) as fp:
        species = json.load(fp)

    fp = open('problems_in_lexical_data.tab', 'w')
    for i, spec in enumerate(species.values()):
        s = data.add(
            models.Species, spec['name'],
            id=slug(spec['name']),
            genus=spec['genus'],
            name=spec['name'],
            description=spec['description'],
            family=spec['family'],
            wikipedia_url=spec['wikipedia'].get('fullurl'),
            eol_id=spec['eol'].get('id'))

        for j, img in enumerate(spec['images']):
            if not img.get('thumbnail'):
                assert img.keys() == ['metadata']
                continue

            for n in ['thumbnail', 'small', 'large']:
                if n not in img or (n == 'small' and 'large' in img):
                    continue
                jsondata = img['metadata']
                jsondata.update(img[n])
                f = common.Parameter_files(
                    object=s,
                    id='%s-%s-%s.jpg' % (s.id, j, n),
                    name='%s %s' % (n, j),
                    jsondata=jsondata,
                    mime_type='image/jpeg')
                f.create(files_dir, wiki.get(args, img[n]['src'], html=False))

        for attr, model in [
            ('categories', models.Category),
            ('countries', models.Country),
            ('ecoregions', models.Ecoregion),
        ]:
            for name in filter(None, spec[attr]):
                if attr == 'countries' and name == "Botswanan":
                    name = "Botswana"
                if name in data[model.mapper_name()]:
                    o = data[model.mapper_name()][name]
                else:
                    if attr == 'countries':
                        _name, _id = COUNTRIES[slug(name)]
                    else:
                        _name, _id = name, slug(name)
                    o = data.add(model, name, id=_id, name=_name)
                o.species.append(s)

        for lang, words in spec['names'].items():
            words = parsed_words(words, fp, lang)
            lang = data['Languoid'][lang]

            if lang.id != 'nmn':
                vs = common.ValueSet(
                    id='%s-%s' % (s.id, lang.id),
                    parameter=s,
                    language=lang,
                    contribution=contrib)
                sources = []
                for ref in chain(*[w[1] for w in words if w[1] is not None]):
                    ref = list(get_refs(spec['references'][int(ref) - 1]))
                    for k, ref_ in enumerate(ref):
                        if isinstance(ref_, basestring):
                            sources.append(ref_)
                        else:
                            ref_, pages = ref_
                            DBSession.add(common.ValueSetReference(
                                valueset=vs, source=data['Bibrec'][ref_], description=pages))
                if sources:
                    vs.source = '; '.join(sources)

            for k, word in enumerate(words):
                word, _refs, varieties = word

                if lang.id.startswith('nmn'):
                    if varieties:
                        assert len(varieties) == 1
                        varieties = [_v.strip() for _v in varieties[0].split(',')]
                        if len(varieties) > 1:
                            #
                            # TODO: needs to be handled!
                            #
                            raise ValueError

                        lang = data['Languoid'][taa_variety_map[varieties[0].strip().lower()]]
                    vsid = '%s-%s' % (s.id, lang.id)
                    if vsid in data['ValueSet']:
                        vs = data['ValueSet'][vsid]
                    else:
                        vs = data.add(
                            common.ValueSet, vsid,
                            id=vsid,
                            parameter=s,
                            language=lang,
                            contribution=contrib)
                        sources = []
                        for ref in chain(*[w[1] for w in words if w[1] is not None and w[2] == varieties]):
                            ref = list(get_refs(spec['references'][int(ref) - 1]))
                            for ref_ in ref:
                                if isinstance(ref_, basestring):
                                    sources.append(ref_)
                                else:
                                    ref_, pages = ref_
                                    DBSession.add(common.ValueSetReference(
                                        valueset=vs, source=data['Bibrec'][ref_], description=pages))
                        if sources:
                            vs.source = '; '.join(sources)

                id_ = '%s-%s-%s' % (s.id, lang.id, k)
                word.valueset = vs
                word.id = id_
                if not lang.id.startswith('nmn'):
                    for v_ in varieties:
                        for v in v_.split(','):
                            v = v.strip()
                            try:
                                word.varieties.append(
                                    data['Variety']['%s-%s' % (lang.id, slug(v))])
                            except KeyError:
                                # Papio ursinus
                                #'Khoekhoegowab': u'\u01c2\xe1\xecd\u0209-\xe0\u01c3\u0151\u1e3fs\xe8.b, \u01c3h\xe0\u0151-kh\xf3m\u0300.mi, \u01c0uisi\u01c2n\xfbu.b (S) [4]'
                                # undefined variety "S"!
                                print '#########', s.name
                                print spec['names']


def from_csv(args, model, data, visitor=None, condition=None, **kw):
    kw.setdefault('delimiter', ',')
    kw.setdefault('lineterminator', str('\r\n'))
    kw.setdefault('quotechar', '"')
    for row in list(reader(args.data_file('dump', model.__csv_name__ + '.csv'), **kw))[1:]:
        if condition and not condition(row):
            continue
        obj = data.add(model, row[0], _obj=model.from_csv(row, data))
        if visitor:
            visitor(obj)


def main(args):
    data, contrib, glottolog = get_metadata()

    refs = wiki.get_refs(args)
    for rec in refs.records:
        data.add(models.Bibrec, rec.id, _obj=bibtex2source(rec, cls=models.Bibrec))

    from_csv(args, models.Bibrec, data, condition=lambda row: row[0] not in data['Bibrec'])

    for model in [
        models.Variety,
        models.Country,
        models.Category,
        models.Ecoregion,
    ]:
        from_csv(args, model, data)

    def visitor(lang):
        if lang.id in glottolog:
            gcode, lat, lon = glottolog[lang.id]
            #
            # TODO: add glottocode!
            #

    from_csv(args, models.Languoid, data, visitor=visitor)
    from_csv(args, models.Species, data)

    #
    # TODO: images, words
    #
    for image in reader(
            args.data_file('dump', 'images.csv'),
            namedtuples=True,
            delimiter=",",
            lineterminator='\r\n'
    ):
        # id,species_id,name,mime_type,src,width,height,author,date,place,comments,keywords,permission
        jsondata = dict(width=int(image.width), height=int(image.height))
        for k in 'src author date place comments keywords permission'.split():
            v = getattr(image, k)
            if v:
                if k == 'permission':
                    jsondata[k] = json.loads(v)
                elif k == 'src':
                    pref = 'https://lingweb.eva.mpg.de'
                    if v.startswith(pref):
                        v = v[len(pref):]
                    jsondata[k] = v
                else:
                    jsondata[k] = v
        f = common.Parameter_files(
            object=data['Species'][image.species_id],
            id=image.id,
            name=image.name,
            jsondata=jsondata,
            mime_type=image.mime_type)
        #
        # TODO: handle new images!?
        #
        #f.create(files_dir, wiki.get(args, img[n]['src'], html=False))

    from_csv(args, models.Word, data)


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """


if __name__ == '__main__':
    initializedb(create=main, prime_cache=prime_cache)
    sys.exit(0)
