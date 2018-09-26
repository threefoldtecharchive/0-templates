
from js9 import j
from JumpScale9Lib.clients.portal.PortalClient import ApiError


def catch_exception_decoration_return(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ApiError as e:
            if e.response.status_code == 401:
                jwt = j.clients.itsyouonline.get(instance="main").jwt_get(refreshable=True)
                self.ovc_data["jwt_"] = jwt
                return wrapper(self, *args, **kwargs)
            else:
                return e.response
    return wrapper
