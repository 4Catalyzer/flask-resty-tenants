import flask
from flask_resty_tenants import TenantAuthorization
import pytest
from sqlalchemy import Column, Integer
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


def test_filtering(db):
    flask.g.resty_request_credentials = {
        'app_metadata': {
            '*': 0,
        }
    }

    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)

    auth = TenantAuthorization()
    assert (auth.get_filter(None) | (Widget.id == 0)) is not None
