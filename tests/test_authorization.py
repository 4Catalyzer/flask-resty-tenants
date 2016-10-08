from uuid import uuid4

import flask
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


def test_bad_credentials(auth, tenant_id):
    flask.g.resty_request_credentials = 'not a valid payload'

    assert not tuple(auth.get_authorized_tenant_ids(0))
    assert auth.get_tenant_role(tenant_id) < 0


def test_bad_role(auth, tenant_id):
    flask.g.resty_request_credentials = {
        'app_metadata': {
            str(tenant_id): None,
        }
    }

    assert not tuple(auth.get_authorized_tenant_ids(0))
    assert auth.get_tenant_role(tenant_id) < 0


def test_bad_default_role(auth, tenant_id):
    flask.g.resty_request_credentials = {
        'app_metadata': {
            str(tenant_id): None,
            '*': None,
        }
    }

    assert not tuple(auth.get_authorized_tenant_ids(0))
    assert auth.get_tenant_role(tenant_id) < 0
    assert auth.get_default_role() < 0


def test_bad_role_other_tenant(auth, tenant_id):
    flask.g.resty_request_credentials = {
        'app_metadata': {
            uuid4(): 'not a valid role',
            str(tenant_id): 2,
        }
    }

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(2)) == (tenant_id,)
    assert auth.get_tenant_role(tenant_id) == 2


def test_bad_tenant(auth, tenant_id):
    flask.g.resty_request_credentials = {
        'app_metadata': {
            'not a valid tenant': 2,
            str(tenant_id): 2,
        }
    }

    assert tuple(auth.get_authorized_tenant_ids(0)) == (tenant_id,)
    assert tuple(auth.get_authorized_tenant_ids(2)) == (tenant_id,)
    assert auth.get_tenant_role(tenant_id) == 2


def test_filtering(db, auth, tenant_id):
    flask.g.resty_request_credentials = {
        'app_metadata': {
            '*': 0,
        }
    }

    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)

    db.create_all()
    db.session.add(Widget())

    assert Widget.query.filter(auth.get_filter(Widget)).first()
    assert auth.get_tenant_role(tenant_id) == 0

    db.drop_all()
