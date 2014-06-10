from sqlalchemy.orm import joinedload, joinedload_all

from clld.web.datatables.base import Col, LinkCol
from clld.web.datatables.parameter import Parameters
from clld.web.datatables.value import Values
from clld.web.datatables.language import Languages
from clld.web.util.helpers import HTML, external_link, linked_references
from clld.db.util import get_distinct_values
from clld.db.meta import DBSession
from clld.db.models.common import Parameter, Value, Language, ValueSet

from tsammalex.models import (
    Ecoregion, SpeciesEcoregion,
    Country, SpeciesCountry,
    Category, SpeciesCategory, Species,
    Word, Variety, WordVariety,
    Languoid,
)


class ThumbnailCol(Col):
    __kw__ = dict(bSearchable=False, bSortable=False)

    def format(self, item):
        item = self.get_obj(item)
        if item.thumbnail:
            return HTML.img(src=self.dt.req.file_url(item.thumbnail))
        return ''


class CatCol(Col):
    __spec__ = (None, None)

    def __init__(self, *args, **kw):
        kw['choices'] = get_distinct_values(self.__spec__[1].name)
        Col.__init__(self, *args, **kw)

    def format(self, item):
        return ', '.join(o.name for o in getattr(item, self.__spec__[0]))

    def search(self, qs):
        return self.__spec__[1].name == qs


class CountryCol(CatCol):
    __spec__ = ('countries', Country)


class CategoryCol(CatCol):
    __spec__ = ('categories', Category)


class EcoregionCol(CatCol):
    __spec__ = ('ecoregions', Ecoregion)

    def __init__(self, *args, **kw):
        kw['choices'] = [
            er.name for er in
            DBSession.query(Ecoregion).join(SpeciesEcoregion).order_by(Ecoregion.id)]
        Col.__init__(self, *args, **kw)


class SpeciesTable(Parameters):
    def base_query(self, query):
        query = query \
            .outerjoin(SpeciesCategory, SpeciesCategory.species_pk == Parameter.pk) \
            .outerjoin(Category, SpeciesCategory.category_pk == Category.pk)\
            .outerjoin(SpeciesCountry, SpeciesCountry.species_pk == Parameter.pk) \
            .outerjoin(Country, SpeciesCountry.country_pk == Country.pk)\
            .outerjoin(SpeciesEcoregion, SpeciesEcoregion.species_pk == Parameter.pk)\
            .outerjoin(Ecoregion, SpeciesEcoregion.ecoregion_pk == Ecoregion.pk)\
            .options(
                joinedload(Species.categories),
                joinedload(Species.ecoregions),
                joinedload(Species.countries))
        return query.distinct()

    def col_defs(self):
        er_col = EcoregionCol(self, 'ecoregions', bSortable=False)
        if 'er' in self.req.params:
            er_col.js_args['sFilter'] = self.req.params['er']
        res = Parameters.col_defs(self)[1:]
        res[0].js_args['sTitle'] = 'Species'
        res.append(Col(self, 'description', sTitle='Name')),
        res.append(Col(self, 'genus', model_col=Species.genus)),
        res.append(Col(self, 'family', model_col=Species.family)),
        res.append(ThumbnailCol(self, 'thumbnail'))
        res.append(CategoryCol(self, 'categories', bSortable=False))
        res.append(er_col)
        res.append(CountryCol(self, 'countries', bSortable=False))
        return res


class RefsCol(Col):
    __kw__ = dict(bSearchable=False, bSortable=False)

    def format(self, item):
        lis = []
        if item.valueset.source:
            s = item.valueset.source
            if s.startswith('http://'):
                label = s
                for t in 'wikimedia wikipedia plantzafrica'.split():
                    if t in s:
                        label = t
                        break
                lis.append(external_link(s, label))
        lis.append(linked_references(self.dt.req, item.valueset))
        return HTML.ul(*lis, class_='unstyled')


class VarietiesCol(Col):
    __kw__ = dict(bSortable=False)

    def search(self, qs):
        return Variety.pk == int(qs)

    def format(self, item):
        return ', '.join(v.name for v in item.varieties)


class Words(Values):
    def base_query(self, query):
        query = Values.base_query(self, query)
        if self.language:
            query = query.outerjoin(WordVariety, Variety)
            query = query.options(joinedload_all(Value.valueset, ValueSet.parameter))
        return query

    def col_defs(self):
        res = []
        if self.language:
            res = [
                ThumbnailCol(self, '_', get_object=lambda i: i.valueset.parameter),
                LinkCol(
                    self, 'species',
                    model_col=Parameter.name,
                    get_object=lambda i: i.valueset.parameter),
                Col(
                    self, 'name',
                    model_col=Parameter.description,
                    get_object=lambda i: i.valueset.parameter),
            ]
        elif self.parameter:
            res = [
                LinkCol(
                    self, 'language',
                    model_col=Language.name,
                    get_object=lambda i: i.valueset.language)
            ]
        res.append(Col(self, 'word', model_col=Value.name))
        if self.language:
            res.append(Col(self, 'exact meaning', model_col=Value.description))
            res.append(Col(self, 'phonetic', model_col=Word.phonetic))
            res.append(Col(self, 'grammatical_info', model_col=Word.grammatical_info))
            if self.language.varieties:
                res.append(VarietiesCol(
                    self, 'variety',
                    choices=[(v.pk, v.name) for v in self.language.varieties]))
        res.append(RefsCol(self, 'references'))
        return res

    def get_options(self):
        if self.parameter:
            return {'bPaginate': False}


class Languoids(Languages):
    def col_defs(self):
        res = Languages.col_defs(self)
        return res[:2] + [Col(self, 'lineage', model_col=Languoid.lineage)] + res[2:]


def includeme(config):
    config.register_datatable('parameters', SpeciesTable)
    config.register_datatable('values', Words)
    config.register_datatable('languages', Languoids)
