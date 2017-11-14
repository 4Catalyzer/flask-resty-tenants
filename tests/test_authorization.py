from uuid import uuid4

from flask_resty import context
from flask_resty_tenants import TenantAuthorization
import pytest
from sqlalchemy import Column, Integer

# -----------------------------------------------------------------------------


@pytest.yield_fixture(autouse=True)
def fake_context(app):
    with app.test_request_context():
        yield


@pytest.fixture
def auth():
    return TenantAuthorization()


@pytest.fixture
def tenant_id():
    return uuid4()


# -----------------------------------------------------------------------------


def test_credentials(auth, tenant_id):
    context.set_context_value('request_credentials', {
        'app_metadata': {
            str(tenant_id): 1,
        }
    })

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(1)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(2)) == ()
    assert auth.is_authorized(tenant_id, 0)
    assert auth.is_authorized(tenant_id, 1)
    assert not auth.is_authorized(tenant_id, 2)


def test_credentials_custom_field(auth, tenant_id):
    context.set_context_value('request_credentials', {
        'app_metadata': {
            str(tenant_id): 1,
        }
    })

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(1)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(2)) == ()
    assert auth.is_authorized(tenant_id, 0)
    assert auth.is_authorized(tenant_id, 1)
    assert not auth.is_authorized(tenant_id, 2)


def test_credentials_custom_role_fields(auth, tenant_id):
    context.set_context_value('request_credentials', {
        'https://foo.com/app_metadata': {
            str(tenant_id): 1,
        }
    })

    auth.role_fields = ('https://foo.com/app_metadata',)

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(1)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(2)) == ()
    assert auth.is_authorized(tenant_id, 0)
    assert auth.is_authorized(tenant_id, 1)
    assert not auth.is_authorized(tenant_id, 2)


def test_global_credentials(auth, tenant_id):
    tenant_id_2 = uuid4()
    tenant_id_3 = uuid4()

    context.set_context_value('request_credentials', {
        'app_metadata': {
            str(tenant_id): 1,
            str(tenant_id_3): -1,
            '*': 0,
        }
    })

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert auth.is_authorized(tenant_id, 1)
    assert auth.is_authorized(tenant_id_2, 0)
    assert auth.is_authorized(tenant_id_3, 0)
    assert not auth.is_authorized(tenant_id_2, 1)
    assert not auth.is_authorized(tenant_id_3, 1)


def test_bad_credentials(auth, tenant_id):
    context.set_context_value('request_credentials', 'not a valid payload')

    assert not tuple(auth.get_authorized_tenant_ids(0))
    assert not auth.is_authorized(tenant_id, 0)


def test_bad_role(auth, tenant_id):
    context.set_context_value('request_credentials', {
        'app_metadata': {
            str(tenant_id): None,
        }
    })

    assert not tuple(auth.get_authorized_tenant_ids(0))
    assert not auth.is_authorized(tenant_id, 0)


def test_bad_global_role(auth, tenant_id):
    context.set_context_value('request_credentials', {
        'app_metadata': {
            str(tenant_id): None,
            '*': None,
        }
    })

    assert not tuple(auth.get_authorized_tenant_ids(0))
    assert not auth.is_authorized(tenant_id, 0)
    assert auth.get_global_role() < 0


def test_bad_role_other_tenant(auth, tenant_id):
    context.set_context_value('request_credentials', {
        'app_metadata': {
            uuid4(): 'not a valid role',
            str(tenant_id): 2,
        }
    })

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(2)) == (tenant_id,)
    assert auth.is_authorized(tenant_id, 2)


def test_bad_tenant(auth, tenant_id):
    context.set_context_value('request_credentials', {
        'app_metadata': {
            'not a valid tenant': 2,
            str(tenant_id): 2,
        }
    })

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(2)) == (tenant_id,)
    assert auth.is_authorized(tenant_id, 2)


def test_filtering(db, auth, tenant_id):
    context.set_context_value('request_credentials', {
        'app_metadata': {
            '*': 0,
        }
    })

    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)

    db.create_all()
    db.session.add(Widget())

    assert auth.filter_query(Widget.query, None).first()
    assert auth.is_authorized(tenant_id, 0)
    assert not auth.is_authorized(tenant_id, 1)

    db.drop_all()
