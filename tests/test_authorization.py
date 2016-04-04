import flask
from flask_resty_tenants import TenantAuthorization
import pytest
from uuid import uuid4

# -----------------------------------------------------------------------------


@pytest.yield_fixture(autouse=True)
def fake_context(app):
    ctx = app.test_request_context()
    ctx.push()
    yield
    ctx.pop()


def test_bad_credentials():
    flask.g.resty_request_credentials = 'not a valid payload'
    # flask.g = MagicMock(resty_request_credentials='not a valid payload')
    auth = TenantAuthorization()
    assert auth.get_tenant_credentials() == {}


def test_bad_role():
    tenant = uuid4()
    flask.g.resty_request_credentials = {
        'app_metadata': {
            uuid4(): 'not a valid role',
            str(tenant): 2,
        }
    }
    auth = TenantAuthorization()
    assert auth.get_tenant_credentials() == {tenant: 2}


def test_bad_tenant():
    tenant = uuid4()
    flask.g.resty_request_credentials = {
        'app_metadata': {
            'not a valid tenant': 2,
            str(tenant): 2,
        }
    }
    auth = TenantAuthorization()
    assert auth.get_tenant_credentials() == {tenant: 2}
