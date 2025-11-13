from functools import wraps
from flask import request, jsonify
try:
    import jwt
except ImportError:
    from jose import jwt
from datetime import datetime
from core.config import Config
from modules.user.models import Usuario


def token_required(f):
    """
    Middleware para verificar token JWT en las peticiones
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Obtener token del header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Formato esperado: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    'error': 'Token mal formado',
                    'message': 'El formato debe ser: Bearer <token>'
                }), 401
        
        if not token:
            return jsonify({
                'error': 'Token no proporcionado',
                'message': 'Se requiere autenticación para acceder a este recurso'
            }), 401
        
        try:
            # Decodificar el token
            payload = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )
            
            # Verificar expiración
            if datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
                return jsonify({
                    'error': 'Token expirado',
                    'message': 'El token ha expirado, por favor inicie sesión nuevamente'
                }), 401
            
            # Obtener usuario de la base de datos
            current_user = Usuario.query.filter_by(id=payload['user_id']).first()
            
            if not current_user:
                return jsonify({
                    'error': 'Usuario no encontrado',
                    'message': 'El usuario asociado al token no existe'
                }), 401
            
            if not current_user.activo:
                return jsonify({
                    'error': 'Usuario inactivo',
                    'message': 'La cuenta de usuario está desactivada'
                }), 401
            
            # Agregar usuario actual al contexto
            request.current_user = current_user
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token expirado',
                'message': 'El token ha expirado, por favor inicie sesión nuevamente'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'error': 'Token inválido',
                'message': 'El token proporcionado no es válido'
            }), 401
        except Exception as e:
            return jsonify({
                'error': 'Error de autenticación',
                'message': str(e)
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated


def optional_token(f):
    """
    Middleware opcional para verificar token JWT
    No requiere token, pero si está presente lo valida y añade el usuario al contexto
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        request.current_user = None
        
        # Obtener token del header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                pass
        
        if token:
            try:
                # Decodificar el token
                payload = jwt.decode(
                    token,
                    Config.JWT_SECRET_KEY,
                    algorithms=[Config.JWT_ALGORITHM]
                )
                
                # Verificar expiración
                if datetime.fromtimestamp(payload['exp']) >= datetime.utcnow():
                    # Obtener usuario de la base de datos
                    current_user = Usuario.query.filter_by(id=payload['user_id']).first()
                    
                    if current_user and current_user.activo:
                        request.current_user = current_user
            except:
                pass  # Token inválido o expirado, pero es opcional
        
        return f(*args, **kwargs)
    
    return decorated
