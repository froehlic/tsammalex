# coding: utf8
# pragma: no cover
from __future__ import unicode_literals, division, absolute_import, print_function
import sys
import json
from itertools import groupby
from functools import partial
import re

from sqlalchemy.orm import joinedload
from clld.scripts.util import (
    initializedb, Data, bibtex2source, glottocodes_by_isocode, add_language_codes,
)
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib.dsv import reader
from clld.lib.imeji import file_urls
from clld.lib.bibtex import Database
from clld.util import nfilter, jsonload

from tsammalex import models
from tsammalex.scripts.util import update_species_data, load_ecoregions, from_csv


def main(args):
    data = Data()
    data.add(common.Dataset, 'tsammalex',
        id="tsammalex",
        name="Tsammalex",
        description="A lexical database on plants and animals (preliminary version)",
        publisher_name="Max Planck Institute for Evolutionary Anthropology",
        publisher_place="Leipzig",
        publisher_url="http://www.eva.mpg.de",
        domain='tsammalex.clld.org',
        license='http://creativecommons.org/licenses/by/4.0/',
        contact='naumann@eva.mpg.de',
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})
    data.add(common.Contribution, 'tsammalex', name="Tsammalex", id="tsammalex")
    glottolog = glottocodes_by_isocode('postgresql://robert@/glottolog3')

    refs = Database.from_file(args.data_file('newdump', 'sources.bib'))
    for rec in refs:
        data.add(models.Bibrec, rec.id, _obj=bibtex2source(rec, cls=models.Bibrec))

    load_ecoregions(args, data)
    from_csv(args, models.Lineage, data)
    from_csv(args, models.Use, data)
    from_csv(args, models.TsammalexContributor, data)

    def visitor(lang, data):
        if lang.id in glottolog:
            add_language_codes(data, lang, lang.id.split('-')[0], glottolog)
        if lang.id == 'eng':
            lang.is_english = True

    from_csv(args, models.Languoid, data, visitor=visitor)
    from_csv(args, models.Country, data)
    from_csv(args, models.Category, data, name='categories')

    def habitat_visitor(cat, data):
        cat.is_habitat = True
    from_csv(args, models.Category, data, name='habitats', visitor=habitat_visitor)

    def species_visitor(eol, species, data):
        species.countries_str = '; '.join([e.name for e in species.countries])
        species.ecoregions_str = '; '.join([e.name for e in species.ecoregions])
        if eol.get(species.id):
            update_species_data(species, eol[species.id])
        else:
            print('--> missing eol id:', species.name)

    eol = jsonload(args.data_file('newdump', 'external', 'eol.json'))
    from_csv(args, models.Species, data, visitor=partial(species_visitor, eol))

    edmond_urls = file_urls(args.data_file('newdump', 'Edmond.xml'))
    edmond_repls = [
        ('damaliscusdorcasphillpsi', 'damaliscuspygargusphillipsi'),
        ('felislybica', 'felissylvestrislybica'),
        ('felisserval', 'leptailurusserval'),
    ]
    type_pattern = re.compile('\-(large|small)\.')
    for image in reader(
            args.data_file('newdump', 'images.csv'),
            namedtuples=True,
            delimiter=",",
            #lineterminator='\r\n'
    ):
        if '-thumbnail' in image.id:
            continue

        id_ = type_pattern.sub('.', image.id)
        edmond_id = id_[:]
        for s, p in edmond_repls:
            edmond_id = edmond_id.replace(p, s)
        if edmond_id not in edmond_urls:
            print('not uploaded? --> %s' % edmond_id)
            continue

        # keywords,permission
        jsondata = edmond_urls[edmond_id]
        for k in 'src creator date place comments permission'.split():
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
            object=data['Species'][image.species__id],
            id=id_,
            name=image.tags,
            jsondata=jsondata,
            mime_type=image.mime_type)
        assert f
        #
        # TODO: handle new images!?
        #
        # upload to edmond, get url back!
        # f.create(files_dir, wiki.get(args, img[n]['src'], html=False))

    from_csv(args, models.Name, data)


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
    for vs in DBSession.query(common.ValueSet).options(
            joinedload(common.ValueSet.values)):
        d = []
        for generic_term, words in groupby(
            sorted(vs.values, key=lambda v: v.description), key=lambda v: v.description
        ):
            if generic_term:
                generic_term += ': '
            else:
                generic_term = ''
            d.append(generic_term + ', '.join(nfilter([w.name for w in words])))

        vs.description = '; '.join(d)

    #
    # TODO: assign ThePlantList ids!
    #


if __name__ == '__main__':
    initializedb(create=main, prime_cache=prime_cache)
    sys.exit(0)
