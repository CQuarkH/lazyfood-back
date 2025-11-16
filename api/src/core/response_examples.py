"""
Ejemplos de uso del manejador centralizado de respuestas y errores

Este archivo muestra cómo usar el ResponseHandler y los mensajes estandarizados
en los endpoints de la API
"""

# FORMA ANTIGUA (inconsistente)
# ================================

# Antes - respuestas inconsistentes:
def old_endpoint():
    # Diferentes formatos de éxito
    return jsonify({'message': 'Usuario creado'}), 201
    return jsonify({'msg': 'OK'}), 200
    return jsonify({'success': True, 'data': data}), 200
    
    # Diferentes formatos de error
    return jsonify({'error': 'Error'}), 400
    return jsonify({'err': 'No encontrado'}), 404
    return jsonify({'message': 'Error interno'}), 500


# FORMA NUEVA (consistente con ResponseHandler)
# ==============================================

from core.response_handler import response, errors, success

# Ejemplo 1: Respuestas de éxito simples
def get_users():
    try:
        usuarios = Usuario.query.all()
        usuarios_list = [u.to_dict() for u in usuarios]
        
        return response.success({
            'total_usuarios': len(usuarios_list),
            'usuarios': usuarios_list
        })
        
    except Exception as e:
        return response.internal_error()


# Ejemplo 2: Crear recurso (201)
def create_user():
    try:
        # ... lógica de creación ...
        nuevo_usuario = Usuario(nombre=nombre, email=email)
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return response.created({
            'id': nuevo_usuario.id,
            'nombre': nuevo_usuario.nombre,
            'email': nuevo_usuario.email
        }, success.USER_CREATED)
        
    except Exception as e:
        return response.internal_error()


# Ejemplo 3: Validaciones y errores 400
def login():
    data = request.get_json()
    
    if not data:
        return response.bad_request(errors.INVALID_DATA)
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return response.bad_request(errors.MISSING_FIELDS)
    
    # ... resto de la lógica ...


# Ejemplo 4: Errores de autenticación (401)
def protected_endpoint():
    token = request.headers.get('Authorization')
    
    if not token:
        return response.unauthorized(errors.TOKEN_MISSING)
    
    try:
        payload = jwt.decode(token, secret_key)
    except jwt.ExpiredSignatureError:
        return response.unauthorized(errors.TOKEN_EXPIRED)
    except jwt.InvalidTokenError:
        return response.unauthorized(errors.TOKEN_INVALID)
    
    # ... resto de la lógica ...


# Ejemplo 5: Errores de autorización (403)
def delete_user(id):
    if request.current_user.id != id:
        return response.forbidden(errors.ONLY_OWN_ACCOUNT)
    
    # ... resto de la lógica ...


# Ejemplo 6: Recurso no encontrado (404)
def get_user(id):
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return response.not_found(errors.USER_NOT_FOUND)
    
    return response.success({'usuario': usuario.to_dict()})


# Ejemplo 7: Conflicto (409)
def register_user():
    email = data.get('email')
    
    if Usuario.query.filter_by(correo=email).first():
        return response.conflict(errors.USER_ALREADY_EXISTS)
    
    # ... resto de la lógica ...


# Ejemplo 8: Usando APIException para errores personalizados
from core.error_handler import APIException

def complex_operation():
    try:
        # ... operación compleja ...
        if condition_failed:
            raise APIException(
                message="Operación no permitida en este momento",
                status_code=422,
                payload={'reason': 'Estado inválido'}
            )
    except APIException:
        raise  # Re-lanzar para que sea capturada por el handler global
    except Exception as e:
        return response.internal_error()


# Ejemplo 9: Respuesta con mensaje personalizado
def update_preferences():
    try:
        # ... lógica de actualización ...
        
        return response.success(
            data={
                'preferencias': {
                    'dieta': dieta,
                    'alergias': alergias,
                    'gustos': gustos
                }
            },
            message=success.PREFERENCES_UPDATED
        )
        
    except Exception as e:
        return response.internal_error()


# RESUMEN DE MÉTODOS DISPONIBLES
# ===============================

# ResponseHandler:
# - response.success(data, message, status_code)
# - response.created(data, message)
# - response.error(message, status_code, details)
# - response.bad_request(message)
# - response.unauthorized(message)
# - response.forbidden(message)
# - response.not_found(message)
# - response.conflict(message)
# - response.internal_error(message)

# ErrorMessages (errors.*):
# - errors.INVALID_DATA
# - errors.MISSING_FIELDS
# - errors.INVALID_CREDENTIALS
# - errors.TOKEN_MISSING
# - errors.TOKEN_INVALID
# - errors.USER_NOT_FOUND
# - errors.USER_ALREADY_EXISTS
# - errors.INTERNAL_ERROR
# ... y más en core/response_handler.py

# SuccessMessages (success.*):
# - success.USER_CREATED
# - success.USER_UPDATED
# - success.LOGIN_SUCCESS
# - success.PREFERENCES_UPDATED
# ... y más en core/response_handler.py
