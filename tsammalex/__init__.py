from __future__ import unicode_literals, absolute_import, division, print_function

from six import string_types
from zope.interface import classImplements

from clld.interfaces import ILanguage, IMapMarker
from clld.web.app import get_configurator, MapMarker
from clld.db.models.common import Parameter_files

# we must make sure custom models are known at database initialization!
from tsammalex import models
from tsammalex.interfaces import IEcoregion, IImage


# associate Parameter_files with the IImage interface to make the model work as resource.
classImplements(Parameter_files, IImage)

_ = lambda s: s
_('Parameter')
_('Parameters')
_('Source')
_('Sources')
_('Value')
_('Values')


class TsammalexMapMarker(MapMarker):
    def get_icon(self, ctx, req):
        lineage = None
        if ctx and isinstance(ctx, (tuple, list)):
            ctx = ctx[0]

        if ILanguage.providedBy(ctx):
            lineage = ctx.lineage

        if isinstance(ctx, string_types):
            lineage = req.db.query(models.Lineage)\
                .filter(models.Lineage.name == ctx).one()

        if lineage:
            return 'c' + lineage.color


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = get_configurator(
        'tsammalex', (TsammalexMapMarker(), IMapMarker), settings=settings)
    config.registry.settings['home_comp'].append('contributors')
    config.include('clldmpg')
    config.register_menu(
        ('dataset', dict(label='Home')),
        'values',
        'languages',
        'parameters',
        'ecoregions',
        'sources',
        'images',
        #('contributors', dict(label='Contribute'))
        ('contribute', lambda ctx, req: (req.route_url('help'), 'Contribute!'))
    )
    config.register_resource('ecoregion', models.Ecoregion, IEcoregion, with_index=True)
    config.register_resource('image', Parameter_files, IImage, with_index=True)
    return config.make_wsgi_app()
