from functools import wraps
from flask import request, jsonify


def role_required(*allowed_roles):
    """
    Middleware para verificar que el usuario tenga uno de los roles permitidos
    
    Args:
        *allowed_roles: Roles permitidos para acceder al endpoint
        
    Uso:
        @role_required('admin')
        @role_required('admin', 'moderador')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar que existe un usuario en el contexto (debe usar token_required antes)
            if not hasattr(request, 'current_user') or request.current_user is None:
                return jsonify({
                    'error': 'No autenticado',
                    'message': 'Debe estar autenticado para acceder a este recurso'
                }), 401
            
            # Verificar que el usuario tenga un rol asignado
            if not hasattr(request.current_user, 'rol') or not request.current_user.rol:
                return jsonify({
                    'error': 'Sin rol asignado',
                    'message': 'El usuario no tiene un rol asignado'
                }), 403
            
            # Verificar que el rol del usuario esté en los roles permitidos
            user_role = request.current_user.rol.lower()
            allowed = [role.lower() for role in allowed_roles]
            
            if user_role not in allowed:
                return jsonify({
                    'error': 'Acceso denegado',
                    'message': f'Se requiere uno de los siguientes roles: {", ".join(allowed_roles)}',
                    'required_roles': list(allowed_roles),
                    'user_role': request.current_user.rol
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def admin_required(f):
    """
    Middleware para verificar que el usuario sea administrador
    Atajo para @role_required('admin')
    """
    return role_required('admin')(f)


def owner_or_admin_required(f):
    """
    Middleware para verificar que el usuario sea el propietario del recurso o un administrador
    Requiere que la función tenga un parámetro 'usuario_id' o 'user_id'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar que existe un usuario en el contexto
        if not hasattr(request, 'current_user') or request.current_user is None:
            return jsonify({
                'error': 'No autenticado',
                'message': 'Debe estar autenticado para acceder a este recurso'
            }), 401
        
        # Si es admin, permitir acceso
        if hasattr(request.current_user, 'rol') and request.current_user.rol.lower() == 'admin':
            return f(*args, **kwargs)
        
        # Obtener el ID del recurso de los argumentos de la ruta
        resource_user_id = kwargs.get('usuario_id') or kwargs.get('user_id')
        
        if not resource_user_id:
            # Si no hay ID en la ruta, verificar en el cuerpo de la petición
            data = request.get_json(silent=True)
            if data:
                resource_user_id = data.get('usuario_id') or data.get('user_id')
        
        # Verificar que el usuario sea el propietario
        if resource_user_id and int(resource_user_id) == request.current_user.id:
            return f(*args, **kwargs)
        
        return jsonify({
            'error': 'Acceso denegado',
            'message': 'Solo puedes acceder a tus propios recursos o debes ser administrador'
        }), 403
    
    return decorated_function
