from flask import Blueprint, jsonify, request
from core.database import db
from modules.user.models import Usuario
from passlib.hash import bcrypt
import secrets
from datetime import datetime, timedelta
import re


user_bp = Blueprint('user', __name__)


# Funciones de validación
def validar_email(email):
    """
    Valida el formato de un correo electrónico
    Returns: (bool, str) - (es_valido, mensaje_error)
    """
    # Patrón regex para validar email
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not email:
        return False, "El correo es obligatorio"
    
    if not re.match(patron, email):
        return False, "El formato del correo electrónico es inválido"
    
    # Validar longitud
    if len(email) > 255:
        return False, "El correo electrónico es demasiado largo"
    
    return True, ""


def validar_password_segura(password):
    """
    Valida que la contraseña sea segura
    Returns: (bool, str) - (es_valida, mensaje_error)
    """
    if not password:
        return False, "La contraseña es obligatoria"
    
    # Longitud mínima
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    # Longitud máxima
    if len(password) > 128:
        return False, "La contraseña es demasiado larga (máximo 128 caracteres)"
    
    # Debe contener al menos una letra mayúscula
    if not re.search(r'[A-Z]', password):
        return False, "La contraseña debe contener al menos una letra mayúscula"
    
    # Debe contener al menos una letra minúscula
    if not re.search(r'[a-z]', password):
        return False, "La contraseña debe contener al menos una letra minúscula"
    
    # Debe contener al menos un número
    if not re.search(r'[0-9]', password):
        return False, "La contraseña debe contener al menos un número"
    
    # Debe contener al menos un carácter especial
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', password):
        return False, "La contraseña debe contener al menos un carácter especial (!@#$%^&*...)"
    
    return True, ""


def validar_nombre(nombre):
    """
    Valida el nombre del usuario
    Returns: (bool, str) - (es_valido, mensaje_error)
    """
    if not nombre:
        return False, "El nombre es obligatorio"
    
    # Longitud mínima
    if len(nombre) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    
    # Longitud máxima
    if len(nombre) > 100:
        return False, "El nombre es demasiado largo (máximo 100 caracteres)"
    
    # Solo letras, espacios, acentos y guiones
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\-]+$', nombre):
        return False, "El nombre solo puede contener letras, espacios y guiones"
    
    return True, ""


@user_bp.route('/v1/usuarios', methods=['GET'])
def listar_usuarios():
    """
    Listar todos los usuarios (solo desarrollo)
    ---
    tags:
      - Usuarios
    responses:
      200:
        description: Lista de usuarios
        schema:
          type: object
          properties:
            total_usuarios:
              type: integer
              example: 3
              description: Total de usuarios en el sistema
            usuarios:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  nombre:
                    type: string
                    example: "Carlos Pérez"
                  correo:
                    type: string
                    example: "carlos@ejemplo.com"
                  pais:
                    type: string
                    example: "Chile"
                  nivel_cocina:
                    type: integer
                    example: 2
                    description: 1=principiante, 2=intermedio, 3=avanzado
                  activo:
                    type: boolean
                    example: true
                  fecha_creacion:
                    type: string
                    format: date-time
                    example: "2024-01-15T10:30:00"
                  preferencias:
                    type: object
                    properties:
                      dieta:
                        type: string
                        example: "vegano"
                      alergias:
                        type: array
                        items:
                          type: string
                        example: ["nueces", "mariscos"]
                      gustos:
                        type: array
                        items:
                          type: string
                        example: ["pasta", "ensaladas", "frutas"]
      500:
        description: Error interno del servidor
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Error interno del servidor"
    """
    try:
        usuarios = Usuario.query.all()

        usuarios_list = []
        for usuario in usuarios:
            usuario_data = usuario.to_dict()
         
            if usuario.preferencias:
                usuario_data['preferencias'] = usuario.preferencias.to_dict()

            usuarios_list.append(usuario_data)

        return jsonify({
            'total_usuarios': len(usuarios_list),
            'usuarios': usuarios_list
        }), 200

    except Exception as e:
        print(f"Error listando usuarios: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@user_bp.route('/v1/usuarios/registro', methods=['POST'])
def registrar_usuario():
    """
    Registrar un nuevo usuario con validaciones de seguridad
    ---
    tags:
      - Usuarios
    parameters:
      - in: body
        name: body
        required: true
        description: Datos del nuevo usuario
        schema:
          type: object
          required:
            - nombre
            - correo
            - password
          properties:
            nombre:
              type: string
              example: "Carlos Pérez"
              description: |
                Nombre completo del usuario
                - Mínimo 2 caracteres, máximo 100
                - Solo letras, espacios y guiones
            correo:
              type: string
              format: email
              example: "carlos@ejemplo.com"
              description: |
                Correo electrónico único del usuario
                - Formato válido requerido
                - Se convierte automáticamente a minúsculas
                - Máximo 255 caracteres
            password:
              type: string
              format: password
              example: "MiContraseña123!"
              description: |
                Contraseña segura del usuario
                - Mínimo 8 caracteres, máximo 128
                - Debe contener al menos una mayúscula
                - Debe contener al menos una minúscula
                - Debe contener al menos un número
                - Debe contener al menos un carácter especial (!@#$%...)
    responses:
      201:
        description: Usuario registrado exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Usuario registrado exitosamente"
            usuario:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                nombre:
                  type: string
                  example: "Carlos Pérez"
                correo:
                  type: string
                  example: "carlos@ejemplo.com"
                pais:
                  type: string
                  nullable: true
                  example: null
                nivel_cocina:
                  type: integer
                  example: 1
                activo:
                  type: boolean
                  example: true
                fecha_creacion:
                  type: string
                  format: date-time
                  example: "2024-01-15T10:30:00"
      400:
        description: Datos inválidos o faltantes
        schema:
          type: object
          properties:
            error:
              type: string
              example: "El nombre, correo y contraseña son obligatorios"
      409:
        description: El correo ya está registrado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "El correo ya está registrado"
      500:
        description: Error interno del servidor
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Error interno del servidor"
    """
    try:
        # Obtener datos del request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No se enviaron datos'}), 400

        # Obtener y limpiar campos
        nombre = data.get('nombre', '').strip()
        correo = data.get('correo', '').strip().lower()
        password = data.get('password', '')

        # Validar que los campos no estén vacíos
        if not nombre or not correo or not password:
            return jsonify({'error': 'El nombre, correo y contraseña son obligatorios'}), 400

        # Validar nombre
        nombre_valido, error_nombre = validar_nombre(nombre)
        if not nombre_valido:
            return jsonify({'error': error_nombre}), 400

        # Validar formato de correo electrónico
        email_valido, error_email = validar_email(correo)
        if not email_valido:
            return jsonify({'error': error_email}), 400

        # Validar que la contraseña sea segura
        password_valida, error_password = validar_password_segura(password)
        if not password_valida:
            return jsonify({'error': error_password}), 400

        # Verificar duplicidad de usuario (correo ya registrado)
        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente:
            return jsonify({
                'error': 'El correo ya está registrado',
                'detalle': 'Ya existe una cuenta con este correo electrónico'
            }), 409

        # Hashear la contraseña de forma segura
        password_hash = bcrypt.hash(password)

        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            correo=correo,
            password=password_hash,
            nivel_cocina=1,  # Por defecto: principiante
            activo=True
        )

        # Guardar en la base de datos
        db.session.add(nuevo_usuario)
        db.session.commit()

        print(f"✓ Usuario registrado exitosamente: {correo}")
        print(f"  Nombre: {nombre}")
        print(f"  ID: {nuevo_usuario.id}")

        return jsonify({
            'mensaje': 'Usuario registrado exitosamente',
            'usuario': nuevo_usuario.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error registrando usuario: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@user_bp.route('/v1/usuarios/detalle', methods=['GET'])
def obtener_usuario():
    """
    Obtener información de un usuario específico por ID
    ---
    tags:
      - Usuarios
    parameters:
      - in: query
        name: userId
        type: integer
        required: true
        description: ID del usuario a buscar
        example: 1
    responses:
      200:
        description: Usuario encontrado
        schema:
          type: object
          properties:
            usuario:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                nombre:
                  type: string
                  example: "Carlos Pérez"
                correo:
                  type: string
                  example: "carlos@ejemplo.com"
                pais:
                  type: string
                  nullable: true
                  example: "Chile"
                nivel_cocina:
                  type: integer
                  example: 2
                  description: 1=principiante, 2=intermedio, 3=avanzado
                activo:
                  type: boolean
                  example: true
                fecha_creacion:
                  type: string
                  format: date-time
                  example: "2024-01-15T10:30:00"
                preferencias:
                  type: object
                  nullable: true
                  properties:
                    dieta:
                      type: string
                      example: "vegano"
                    alergias:
                      type: array
                      items:
                        type: string
                      example: ["nueces", "mariscos"]
                    gustos:
                      type: array
                      items:
                        type: string
                      example: ["pasta", "ensaladas"]
      400:
        description: Parámetro userId faltante o inválido
        schema:
          type: object
          properties:
            error:
              type: string
              example: "El parámetro userId es obligatorio"
      404:
        description: Usuario no encontrado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuario no encontrado"
      500:
        description: Error interno del servidor
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Error interno del servidor"
    """
    try:
  
        user_id = request.args.get('userId')
        

        if not user_id:
            return jsonify({'error': 'El parámetro userId es obligatorio'}), 400
        

        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({'error': 'El userId debe ser un número válido'}), 400
        
  
        usuario = Usuario.query.get(user_id)
        

        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        

        usuario_data = usuario.to_dict()
        
   
        if usuario.preferencias:
            usuario_data['preferencias'] = usuario.preferencias.to_dict()
        
        return jsonify({'usuario': usuario_data}), 200

    except Exception as e:
        print(f"Error obteniendo usuario: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@user_bp.route('/v1/usuarios/recuperar-password', methods=['POST'])
def recuperar_password():
    """
    Solicitar recuperación de contraseña por ID de usuario
    ---
    tags:
      - Usuarios
    parameters:
      - in: query
        name: userId
        type: integer
        required: true
        description: ID del usuario que solicita recuperar contraseña
        example: 1
    responses:
      200:
        description: Solicitud de recuperación procesada exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Enlace de recuperación generado exitosamente"
            link_recuperacion:
              type: string
              example: "http://localhost:5000/reset-password?token=abc123xyz456..."
              description: Link de recuperación (solo en desarrollo)
            token:
              type: string
              example: "abc123xyz456def789..."
              description: Token de recuperación (solo en desarrollo)
            expiracion:
              type: string
              format: date-time
              example: "2025-10-23T13:30:45"
              description: Fecha de expiración del token (1 hora)
            correo:
              type: string
              example: "car***@ejemplo.com"
              description: Correo enmascarado donde se envió el link
      400:
        description: Parámetro userId faltante o inválido
        schema:
          type: object
          properties:
            error:
              type: string
              example: "El parámetro userId es obligatorio"
      404:
        description: Usuario no encontrado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuario no encontrado"
      500:
        description: Error interno del servidor
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Error interno del servidor"
    """
    try:
      
        user_id = request.args.get('userId')
        
      
        if not user_id:
            return jsonify({'error': 'El parámetro userId es obligatorio'}), 400

        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({'error': 'El userId debe ser un número válido'}), 400
        
      
        usuario = Usuario.query.get(user_id)
        
  
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

       
        token = secrets.token_urlsafe(32)
        expiracion = datetime.utcnow() + timedelta(hours=1)

    
        link_recuperacion = f"http://localhost:5000/reset-password?token={token}"

      
        correo = usuario.correo
        partes = correo.split('@')
        if len(partes[0]) > 3:
            correo_enmascarado = f"{partes[0][:3]}***@{partes[1]}"
        else:
            correo_enmascarado = f"{partes[0][0]}***@{partes[1]}"

        
        print(f"✓ Token de recuperación generado para usuario ID: {user_id}")
        print(f"  Correo: {correo}")
        print(f"  Link: {link_recuperacion}")
        print(f"  Expira: {expiracion}")

        # TODO: 

        return jsonify({
            'mensaje': 'Enlace de recuperación generado exitosamente',
            'correo': correo_enmascarado,
           
            'link_recuperacion': link_recuperacion,
            'token': token,
            'expiracion': expiracion.isoformat()
        }), 200

    except Exception as e:
        print(f"Error procesando recuperación de contraseña: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
