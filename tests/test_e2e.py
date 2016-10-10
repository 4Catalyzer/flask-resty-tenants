import flask
from flask_resty import Api, AuthenticationBase, GenericModelView
from flask_resty_tenants import ADMIN, TenantAuthorization
from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer, String

from helpers import assert_response, request

# -----------------------------------------------------------------------------

TENANT_ID_1 = 'tenant_1'
TENANT_ID_2 = 'tenant_2'
TENANT_ID_3 = 'tenant_3'

USER_CREDENTIALS = {TENANT_ID_1: 0, TENANT_ID_2: 1}
USER_READ_CREDENTIALS = {TENANT_ID_1: 0, TENANT_ID_2: 0}
USER_ADMIN_CREDENTIALS = {TENANT_ID_1: 0, TENANT_ID_2: 2}

DEFAULT_WRITE_CREDENTIALS = {'*': 1}
DEFAULT_READ_CREDENTIALS = {'*': 0}
DEFAULT_ADMIN_CREDENTIALS = {'*': 2}

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)
        tenant_id = Column(String)
        name = Column(String)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        owner_id = fields.String()
        name = fields.String()
        tenant_id = fields.String()

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture
def auth():
    # dummy authentication based on query params
    class Authentication(AuthenticationBase):
        def get_request_credentials(self):
            return {
                'app_metadata': {
                    k: int(v) for k, v in flask.request.args.items()
                }
            }

    class Authorization(TenantAuthorization):
        tenant_id_type = str

    class AdminAuthorization(TenantAuthorization):
        read_role = ADMIN
        modify_role = ADMIN

        tenant_id_type = str

    return {
        'authentication': Authentication(),
        'authorization': Authorization(),
        'adminAuthorization': AdminAuthorization(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas, auth):
    class WidgetViewBase(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

        authentication = auth['authentication']
        authorization = auth['authorization']

    class WidgetListView(WidgetViewBase):
        def get(self):
            return self.list()

        def post(self):
            return self.create()

    class TenantWidgetListView(WidgetViewBase):
        def get(self, tenant_id):
            return self.list()

    class WidgetView(WidgetViewBase):
        def get(self, id):
            return self.retrieve(id)

        def patch(self, id):
            return self.update(id, partial=True)

        def delete(self, id):
            return self.destroy(id)

    class AdminWidgetView(WidgetViewBase):
        authorization = auth['adminAuthorization']

        def get(self, id):
            return self.retrieve(id)

        def patch(self, id):
            return self.update(id, partial=True)

        def delete(self, id):
            return self.destroy(id)

    api = Api(app)
    api.add_resource(
        '/widgets', WidgetListView, WidgetView, id_rule='<int:id>'
    )
    api.add_resource(
        '/tenants/<tenant_id>/widgets', TenantWidgetListView,
    )
    api.add_resource(
        '/admin_widgets/<int:id>', AdminWidgetView,
    )


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all((
        models['widget'](tenant_id=TENANT_ID_1, name='Foo'),
        models['widget'](tenant_id=TENANT_ID_2, name='Bar'),
        models['widget'](tenant_id=TENANT_ID_3, name='Baz'),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_list(client):
    response = client.get('/widgets', query_string=USER_CREDENTIALS)
    assert_response(response, 200, [
        {'name': 'Foo'},
        {'name': 'Bar'},
    ])


@pytest.mark.parametrize('tenant_id, result', (
    (TENANT_ID_1, 200),
    (TENANT_ID_2, 200),
    (TENANT_ID_3, 404),
))
def test_list(client, tenant_id, result):
    response = client.get(
        '/tenants/{}/widgets'.format(tenant_id),
        query_string=USER_CREDENTIALS,
    )
    assert_response(response, result)


@pytest.mark.parametrize('credentials, result', (
    (USER_READ_CREDENTIALS, 200),
    (USER_CREDENTIALS, 200),
    (DEFAULT_READ_CREDENTIALS, 200),
    (DEFAULT_WRITE_CREDENTIALS, 200),
    (None, 404),
))
def test_retrieve(client, credentials, result):
    response = client.get('/widgets/1', query_string=credentials)
    assert_response(response, result)


@pytest.mark.parametrize('credentials, result', (
    (USER_READ_CREDENTIALS, 404),
    (USER_CREDENTIALS, 404),
    (DEFAULT_READ_CREDENTIALS, 404),
    (DEFAULT_WRITE_CREDENTIALS, 404),
    (None, 404),
    (USER_ADMIN_CREDENTIALS, 200),
    (DEFAULT_ADMIN_CREDENTIALS, 200),
))
def test_admin_retrieve(client, credentials, result):
    response = client.get('/admin_widgets/2', query_string=credentials)
    assert_response(response, result)


@pytest.mark.parametrize('credentials, result', (
    (USER_READ_CREDENTIALS, 403),
    (USER_CREDENTIALS, 201),
    (DEFAULT_READ_CREDENTIALS, 403),
    (DEFAULT_WRITE_CREDENTIALS, 201),
    (None, 403),
))
def test_create(client, credentials, result):
    response = request(
        client,
        'POST', '/widgets',
        {
            'name': 'Created',
            'tenant_id': TENANT_ID_2,
        },
        query_string=credentials,
    )
    assert_response(response, result)


@pytest.mark.parametrize('credentials, result', (
    (USER_READ_CREDENTIALS, 403),
    (USER_CREDENTIALS, 204),
    (DEFAULT_READ_CREDENTIALS, 403),
    (DEFAULT_WRITE_CREDENTIALS, 204),
    (None, 404),
))
def test_update(client, credentials, result):
    response = request(
        client,
        'PATCH', '/widgets/2',
        {
            'id': '2',
            'name': 'Updated',
        },
        query_string=credentials,
    )
    assert_response(response, result)


@pytest.mark.parametrize('credentials, result', (
    (USER_READ_CREDENTIALS, 404),
    (USER_CREDENTIALS, 404),
    (DEFAULT_READ_CREDENTIALS, 404),
    (DEFAULT_WRITE_CREDENTIALS, 404),
    (None, 404),
    (USER_ADMIN_CREDENTIALS, 204),
    (DEFAULT_ADMIN_CREDENTIALS, 204),
))
def test_admin_update(client, credentials, result):
    response = request(
        client,
        'PATCH', '/admin_widgets/2',
        {
            'id': '2',
            'name': 'Updated',
        },
        query_string=credentials,
    )
    assert_response(response, result)


@pytest.mark.parametrize('credentials, result', (
    (USER_READ_CREDENTIALS, 403),
    (USER_CREDENTIALS, 204),
    (DEFAULT_READ_CREDENTIALS, 403),
    (DEFAULT_WRITE_CREDENTIALS, 204),
    (None, 404),
))
def test_delete(client, credentials, result):
    response = client.delete('/widgets/2', query_string=credentials)
    assert_response(response, result)


@pytest.mark.parametrize('credentials, result', (
    (USER_READ_CREDENTIALS, 404),
    (USER_CREDENTIALS, 404),
    (DEFAULT_READ_CREDENTIALS, 404),
    (DEFAULT_WRITE_CREDENTIALS, 404),
    (None, 404),
    (USER_ADMIN_CREDENTIALS, 204),
    (DEFAULT_ADMIN_CREDENTIALS, 204),
))
def test_admin_delete(client, credentials, result):
    response = client.delete('/admin_widgets/2', query_string=credentials)
    assert_response(response, result)
