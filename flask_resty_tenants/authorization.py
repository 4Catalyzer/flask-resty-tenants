from uuid import UUID

import flask

from flask_resty import (
    ApiError,
    AuthorizeModifyMixin,
    HasCredentialsAuthorizationBase,
)
from flask_resty.utils import settable_property

# -----------------------------------------------------------------------------

PUBLIC = float('-inf')
READ_ONLY = 0
MEMBER = 1
ADMIN = 2
NOT_ALLOWED = float('inf')

# -----------------------------------------------------------------------------


class TenantAuthorization(
    AuthorizeModifyMixin,
    HasCredentialsAuthorizationBase,
):
    read_role = READ_ONLY
    modify_role = MEMBER

    role_field = 'app_metadata'

    global_tenant = '*'
    tenant_id_type = UUID
    tenant_id_field = 'tenant_id'

    @settable_property
    def save_role(self):
        return self.modify_role

    @settable_property
    def create_role(self):
        return self.modify_role

    @settable_property
    def update_role(self):
        return self.modify_role

    @settable_property
    def delete_role(self):
        return self.modify_role

    def get_request_tenant_id(self):
        return flask.request.view_args[self.tenant_id_field]

    def get_model_tenant_id(self, model):
        return self.get_tenant_id(model)

    def get_item_tenant_id(self, item):
        return self.get_tenant_id(item)

    def get_tenant_id(self, model_or_item):
        return getattr(model_or_item, self.tenant_id_field)

    def get_data_tenant_id(self, data):
        return data[self.tenant_id_field]

    def get_role_data(self):
        return self.get_credentials_dict_value(self.role_field)

    def get_credentials_dict_value(self, key):
        try:
            value = self.get_request_credentials()[key]
        except (TypeError, KeyError):
            value = {}
        return value if isinstance(value, dict) else {}

    def ensure_role(self, role):
        return role if isinstance(role, int) else PUBLIC

    def get_global_role(self):
        role = self.get_role_data().get(self.global_tenant, PUBLIC)
        return self.ensure_role(role)

    def get_tenant_role(self, tenant_id):
        global_role = self.get_global_role()
        try:
            role = self.ensure_role(self.get_role_data()[str(tenant_id)])
        except KeyError:
            return global_role
        return max(role, global_role)

    def get_authorized_tenant_ids(self, required_role):
        tenant_ids = []

        for tenant_id, tenant_role in self.get_role_data().items():
            try:
                tenant_id = self.tenant_id_type(tenant_id)
            except (TypeError, AttributeError, ValueError):
                continue

            if not isinstance(tenant_role, int):
                continue
            if tenant_role < required_role:
                continue

            tenant_ids.append(tenant_id)

        return frozenset(tenant_ids)

    def is_authorized(self, tenant_id, required_role):
        return self.get_tenant_role(tenant_id) >= required_role

    def authorize_request(self):
        super(TenantAuthorization, self).authorize_request()
        self.check_request_tenant_id()

    def check_request_tenant_id(self):
        try:
            tenant_id = self.get_request_tenant_id()
        except KeyError:
            return

        if self.get_tenant_role(tenant_id) < self.read_role:
            flask.abort(404)

    def filter_query(self, query, view):
        if self.get_global_role() >= self.read_role:
            return query

        return query.filter(self.get_filter(view))

    def get_filter(self, view):
        return self.get_model_tenant_id(view.model).in_(
            self.get_authorized_tenant_ids(self.read_role),
        )

    def authorize_update_item(self, item, data):
        self.authorize_update_item_tenant_id(item, data)
        super(TenantAuthorization, self).authorize_update_item(item, data)

    def authorize_update_item_tenant_id(self, item, data):
        try:
            data_tenant_id = self.get_data_tenant_id(data)
        except KeyError:
            pass
        else:
            if data_tenant_id != self.get_item_tenant_id(item):
                raise ApiError(403, {'code': 'invalid_data.tenant'})

    def authorize_modify_item(self, item, action):
        required_role = self.get_required_role(action)
        self.authorize_item_tenant_role(item, required_role)

    def get_required_role(self, action):
        return getattr(self, '{}_role'.format(action))

    def authorize_item_tenant_role(self, item, required_role):
        tenant_id = self.get_item_tenant_id(item)
        if not self.is_authorized(tenant_id, required_role):
            raise ApiError(403, {'code': 'invalid_tenant.role'})
