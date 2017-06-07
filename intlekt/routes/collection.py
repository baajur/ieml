from flask_mongorest.views import ResourceView
from flask_mongorest.resources import Resource
from flask_mongorest import methods

from intlekt import api

from .document import DocumentResource
from ..models import Collection


class CollectionResource(Resource):
    document = Collection


@api.register(name='collections', url='/collections/')
class CollectionView(ResourceView):
    resource = CollectionResource
    related_resources = {
        'documents': DocumentResource,
    }
    methods = [methods.Create, methods.Update, methods.Fetch, methods.List]