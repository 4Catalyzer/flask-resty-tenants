from flask_resty import ApiError, HasCredentialsAuthorizationBase
from sqlalchemy import sql
from uuid import UUID

# -----------------------------------------------------------------------------

NO_ACCESS = float('-inf')
READ_ONLY = 0
MEMBER = 1
ADMIN = 2

# -----------------------------------------------------------------------------


class TenantCredentials(dict):

    def __init__(self, metadata_location='app_metadata'):
        self.default_credentials = NO_ACCESS

    def get_permissions_for(self, tenant_id):
        return self.get(tenant_id, self.default_credentials)


class TenantAuthorization(HasCredentialsAuthorizationBase):

    read_role = READ_ONLY
    delete_role = MEMBER
    update_role = MEMBER
    save_role = MEMBER
    id_type = UUID
    default_tenant = '*'

    def get_metadata(self):
        return self.get_request_credentials()['app_metadata']

    def get_tenant_credentials(self):
        try:
            app_metadata_items = self.get_metadata().items()
        except (TypeError, KeyError):
            app_metadata_items = ()

        tenant_credentials = TenantCredentials()

        for tenant_id, role in app_metadata_items:
            if type(role) is not int:
                continue
            if tenant_id == self.default_tenant:
                tenant_credentials.default_credentials = role
                continue
            try:
                tenant_id = self.id_type(tenant_id)
            except (AttributeError, ValueError):
                continue

            tenant_credentials[tenant_id] = role

        return tenant_credentials

    def get_filter(self, view):
        credentials = self.get_tenant_credentials()
        if credentials.default_credentials >= self.read_role:
            return sql.true()
        readable_tenants = {
            tenant for tenant, role in credentials.items()
            if role >= self.read_role
        }
        return view.model.tenant_id.in_(readable_tenants)

    def filter_query(self, query, view):
        return query.filter(self.get_filter(view))

    def get_tenant_from_item(self, item):
        return item.tenant_id

    def authorize_save_item(self, item):
        self.authorize_modify_item(item, self.save_role)

    def authorize_update_item(self, item, data):
        self.authorize_modify_item(item, self.update_role)

    def authorize_delete_item(self, item):
        self.authorize_modify_item(item, self.delete_role)

    def authorize_modify_item(self, item, role):
        credentials = self.get_tenant_credentials()
        tenant_id = self.get_tenant_from_item(item)
        if credentials.get_permissions_for(tenant_id) < role:
            raise ApiError(403, {'code': 'invalid_tenant.role'})
