from functools import wraps
from flask import abort
from flask_login import current_user



def role_required(role_name):
    """ Decorator que restringe o acesso a usuários com um papel específico.
    :param role_name: O nome do papel requerido (ex: 'admin' ou UserRole.ADMIN)."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verifica se o usuário está autenticado

            if not current_user.is_authenticated:
                 return abort(401)
            

            if current_user.role != role_name:
                return abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator