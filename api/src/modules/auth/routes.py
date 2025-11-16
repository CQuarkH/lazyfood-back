from flask import Blueprint, jsonify, request
from core.database import db
from modules.user.models import Usuario, Token
from core.auth_middleware import token_required
import bcrypt

try:
    import jwt
except ImportError:
    from jose import jwt
from datetime import datetime, timedelta
from core.config import Config

auth_bp = Blueprint('auth', __name__)


def generar_token(usuario_id, tipo='access'):
    """
    Genera un token JWT para un usuario

    Args:
        usuario_id: ID del usuario
        tipo: 'access' o 'refresh'
    """
    if tipo == 'access':
        expiracion = datetime.utcnow() + timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
    else:  # refresh
        expiracion = datetime.utcnow() + timedelta(seconds=Config.JWT_REFRESH_TOKEN_EXPIRES)

    payload = {
        'user_id': usuario_id,
        'exp': expiracion,
        'iat': datetime.utcnow(),
        'type': tipo
    }

    token = jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )

    return token, expiracion


@auth_bp.route('/v1/auth/login', methods=['POST'])
def login():
    """
    Iniciar sesión y obtener tokens de acceso
    ---
    tags:
      - Autenticación
    parameters:
      - in: body
        name: body
        required: true
        description: Credenciales de inicio de sesión
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: "carlos@email.com"
              description: Correo electrónico del usuario
            password:
              type: string
              example: "Passw0rd"
              description: Contraseña del usuario
    responses:
      200:
        description: Inicio de sesión exitoso
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Inicio de sesión exitoso"
            access_token:
              type: string
              description: Token JWT de acceso
            refresh_token:
              type: string
              description: Token JWT de refresco
            token_type:
              type: string
              example: "Bearer"
            expires_in:
              type: integer
              example: 3600
              description: Tiempo de expiración en segundos
            user:
              type: object
              properties:
                id:
                  type: integer
                nombre:
                  type: string
                correo:
                  type: string
                rol:
                  type: string
      400:
        description: Datos faltantes o inválidos
      401:
        description: Credenciales inválidas
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()

        # Validar datos requeridos
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400

        correo = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not correo or not password:
            return jsonify({'error': 'Email y contraseña son requeridos'}), 400

        # Buscar usuario por correo
        usuario = Usuario.query.filter_by(correo=correo).first()

        if not usuario:
            return jsonify({
                'error': 'Credenciales inválidas',
                'message': 'El correo o la contraseña son incorrectos'
            }), 401

        # Verificar que el usuario esté activo
        if not usuario.activo:
            return jsonify({
                'error': 'Cuenta inactiva',
                'message': 'Tu cuenta ha sido desactivada. Contacta al administrador.'
            }), 401

        # Verificar contraseña
        if not bcrypt.checkpw(password.encode('utf-8'), usuario.password.encode('utf-8')):
            return jsonify({
                'error': 'Credenciales inválidas',
                'message': 'El correo o la contraseña son incorrectos'
            }), 401

        # Generar tokens
        access_token, access_exp = generar_token(usuario.id, tipo='access')
        refresh_token, refresh_exp = generar_token(usuario.id, tipo='refresh')

        # Guardar refresh token en la base de datos
        nuevo_token = Token(
            usuario_id=usuario.id,
            jwt=refresh_token,
            fecha_expiracion=refresh_exp
        )
        db.session.add(nuevo_token)
        db.session.commit()

        return jsonify({
            'message': 'Inicio de sesión exitoso',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': Config.JWT_ACCESS_TOKEN_EXPIRES,
            'user': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'email': usuario.correo,
                'rol': usuario.rol
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error en login: {str(e)}")
        return jsonify({
            'error': 'Error interno del servidor',
            'message': str(e)
        }), 500


@auth_bp.route('/v1/auth/logout', methods=['POST'])
@token_required
def logout():
    """
    Cerrar sesión e invalidar tokens
    ---
    tags:
      - Autenticación
    security:
      - Bearer: []
    responses:
      200:
        description: Cierre de sesión exitoso
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cierre de sesión exitoso"
      401:
        description: No autenticado
      500:
        description: Error interno del servidor
    """
    try:
        # Eliminar todos los tokens del usuario
        Token.query.filter_by(usuario_id=request.current_user.id).delete()
        db.session.commit()

        return jsonify({
            'message': 'Cierre de sesión exitoso'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error en logout: {str(e)}")
        return jsonify({
            'error': 'Error interno del servidor',
            'message': str(e)
        }), 500


@auth_bp.route('/v1/auth/refresh', methods=['POST'])
def refresh():
    """
    Obtener un nuevo access token usando el refresh token
    ---
    tags:
      - Autenticación
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - refresh_token
          properties:
            refresh_token:
              type: string
              description: Token de refresco
    responses:
      200:
        description: Token renovado exitosamente
        schema:
          type: object
          properties:
            access_token:
              type: string
            token_type:
              type: string
              example: "Bearer"
            expires_in:
              type: integer
      400:
        description: Token de refresco no proporcionado
      401:
        description: Token inválido o expirado
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()

        if not data or 'refresh_token' not in data:
            return jsonify({'error': 'Se requiere refresh_token'}), 400

        refresh_token = data['refresh_token']

        # Verificar el refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )

            # Verificar que sea un refresh token
            if payload.get('type') != 'refresh':
                return jsonify({'error': 'Token inválido'}), 401

            # Verificar que el token exista en la base de datos
            token_db = Token.query.filter_by(
                usuario_id=payload['user_id'],
                jwt=refresh_token
            ).first()

            if not token_db:
                return jsonify({'error': 'Token no encontrado'}), 401

            # Verificar que no haya expirado
            if token_db.is_expired():
                db.session.delete(token_db)
                db.session.commit()
                return jsonify({'error': 'Token expirado'}), 401

            # Verificar que el usuario exista y esté activo
            usuario = Usuario.query.get(payload['user_id'])
            if not usuario or not usuario.activo:
                return jsonify({'error': 'Usuario no válido'}), 401

            # Generar nuevo access token
            access_token, _ = generar_token(usuario.id, tipo='access')

            return jsonify({
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': Config.JWT_ACCESS_TOKEN_EXPIRES
            }), 200

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401

    except Exception as e:
        print(f"Error en refresh: {str(e)}")
        return jsonify({
            'error': 'Error interno del servidor',
            'message': str(e)
        }), 500