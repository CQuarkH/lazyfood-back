from flask import Blueprint, jsonify, request
from core.database import db
from modules.user.models import Usuario, Preferencia
from core.auth_middleware import token_required
from core.role_middleware import role_required, admin_required, owner_or_admin_required
import bcrypt
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
@token_required
@admin_required
def listar_usuarios():
    """
    Listar todos los usuarios (solo administradores)
    ---
    tags:
      - Usuarios
    security:
      - Bearer: []
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
            - email
            - password
          properties:
            nombre:
              type: string
              example: "Carlos"
              description: |
                Nombre completo del usuario
                - Mínimo 2 caracteres, máximo 100
                - Solo letras, espacios y guiones
            email:
              type: string
              format: email
              example: "carlos@email.com"
              description: |
                Correo electrónico único del usuario
                - Formato válido requerido
                - Se convierte automáticamente a minúsculas
                - Máximo 255 caracteres
            password:
              type: string
              format: password
              example: "Passw0rd"
              description: |
                Contraseña segura del usuario
                - Mínimo 8 caracteres, máximo 128
                - Debe contener al menos una mayúscula
                - Debe contener al menos una minúscula
                - Debe contener al menos un número
                - Debe contener al menos un carácter especial (!@#$%...)
            pais:
              type: string
              example: "Chile"
              description: País del usuario
            preferencias:
              type: object
              description: Preferencias alimentarias del usuario
              properties:
                dieta:
                  type: string
                  example: "vegano"
                  description: Tipo de dieta (vegano, vegetariano, keto, etc.)
                alergias:
                  type: array
                  items:
                    type: string
                  example: ["maní", "gluten"]
                  description: Lista de alergias alimentarias
                gustos:
                  type: array
                  items:
                    type: string
                  example: ["pasta", "frutas"]
                  description: Lista de preferencias alimentarias
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
            return jsonify({'error': 'Datos inválidos'}), 400

        # Obtener y limpiar campos (ahora se acepta "email" en lugar de "correo")
        nombre = data.get('nombre', '').strip()
        correo = data.get('email', '').strip().lower()
        password = data.get('password', '')
        pais = data.get('pais', '').strip() if data.get('pais') else None
        preferencias_data = data.get('preferencias')

        # Validar que los campos no estén vacíos
        if not nombre or not correo or not password:
            return jsonify({'error': 'Datos inválidos'}), 400

        # Validar nombre
        nombre_valido, error_nombre = validar_nombre(nombre)
        if not nombre_valido:
            return jsonify({'error': 'Datos inválidos'}), 400

        # Validar formato de correo electrónico
        email_valido, error_email = validar_email(correo)
        if not email_valido:
            return jsonify({'error': 'Datos inválidos'}), 400

        # Validar que la contraseña sea segura
        password_valida, error_password = validar_password_segura(password)
        if not password_valida:
            return jsonify({'error': 'Datos inválidos'}), 400

        # Verificar duplicidad de usuario (correo ya registrado)
        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente:
            return jsonify({'error': 'Usuario ya registrado.'}), 409

        # Hashear la contraseña de forma segura
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            correo=correo,
            password=password_hash,
            pais=pais,
            nivel_cocina=1,  # Por defecto: principiante
            activo=True
        )

        # Guardar en la base de datos
        db.session.add(nuevo_usuario)
        db.session.flush()  # Para obtener el ID del usuario antes de commit

        # Crear preferencias si se proporcionaron
        if preferencias_data and isinstance(preferencias_data, dict):
            dieta = preferencias_data.get('dieta')
            alergias = preferencias_data.get('alergias', [])
            gustos = preferencias_data.get('gustos', [])
            
            # Validar que alergias y gustos sean listas
            if not isinstance(alergias, list):
                alergias = []
            if not isinstance(gustos, list):
                gustos = []
            
            nueva_preferencia = Preferencia(
                usuario_id=nuevo_usuario.id,
                dieta=dieta,
                alergias=alergias,
                gustos=gustos
            )
            db.session.add(nueva_preferencia)

        db.session.commit()

        print(f"✓ Usuario registrado exitosamente: {correo}")
        print(f"  Nombre: {nombre}")
        print(f"  ID: {nuevo_usuario.id}")
        print(f"  País: {pais}")
        if preferencias_data:
            print(f"  Preferencias: {preferencias_data}")

        # Preparar respuesta con solo los datos solicitados
        response_data = {
            'mensaje': 'Usuario creado correctamente',
            'id': nuevo_usuario.id,
            'nombre': nuevo_usuario.nombre,
            'email': nuevo_usuario.correo,
            'pais': nuevo_usuario.pais,
            'fecha_creacion': nuevo_usuario.fecha_creacion.isoformat() if nuevo_usuario.fecha_creacion else None
        }
        
        # Agregar preferencias si existen
        if nuevo_usuario.preferencias:
            response_data['preferencias'] = {
                'dieta': nuevo_usuario.preferencias.dieta,
                'alergias': nuevo_usuario.preferencias.alergias or [],
                'gustos': nuevo_usuario.preferencias.gustos or []
            }

        return jsonify(response_data), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error registrando usuario: {str(e)}")
        return jsonify({'error': 'Ocurrió un error interno. Intente más tarde.'}), 500


@user_bp.route('/v1/usuarios/<int:id>', methods=['GET'])
@token_required
def obtener_usuario(id):
    """
    Obtener información de un usuario específico por ID
    ---
    tags:
      - Usuarios
    security:
      - Bearer: []
    parameters:
      - in: path
        name: id
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
        # El ID viene como parámetro de ruta
        usuario = Usuario.query.get(id)
        

        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        

        usuario_data = usuario.to_dict()
        
   
        if usuario.preferencias:
            usuario_data['preferencias'] = usuario.preferencias.to_dict()
        
        return jsonify({'usuario': usuario_data}), 200

    except Exception as e:
        print(f"Error obteniendo usuario: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@user_bp.route('/v1/usuarios/preferencias', methods=['PUT'])
@token_required
def actualizar_preferencias():
    """
    Actualizar las preferencias alimentarias de un usuario
    ---
    tags:
      - Usuarios
    security:
      - Bearer: []
    parameters:
      - in: query
        name: userId
        type: integer
        required: true
        description: ID del usuario
        example: 1
      - in: body
        name: body
        required: true
        description: Nuevas preferencias del usuario
        schema:
          type: object
          properties:
            dieta:
              type: string
              example: "vegano"
              description: Tipo de dieta
            alergias:
              type: array
              items:
                type: string
              example: ["maní", "gluten"]
              description: Lista de alergias
            gustos:
              type: array
              items:
                type: string
              example: ["pasta", "frutas"]
              description: Lista de gustos alimentarios
    responses:
      200:
        description: Preferencias actualizadas exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Preferencias actualizadas exitosamente"
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
                  example: ["maní", "gluten"]
                gustos:
                  type: array
                  items:
                    type: string
                  example: ["pasta", "frutas"]
      400:
        description: Datos inválidos
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Datos inválidos"
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
              example: "Ocurrió un error interno. Intente más tarde."
    """
    try:
        user_id = request.args.get('userId')
        
        if not user_id:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        usuario = Usuario.query.get(user_id)
        
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Obtener datos de preferencias
        dieta = data.get('dieta')
        alergias = data.get('alergias', [])
        gustos = data.get('gustos', [])
        
        # Validar que alergias y gustos sean listas
        if not isinstance(alergias, list):
            alergias = []
        if not isinstance(gustos, list):
            gustos = []
        
        # Verificar si el usuario ya tiene preferencias
        if usuario.preferencias:
            # Actualizar preferencias existentes
            usuario.preferencias.dieta = dieta
            usuario.preferencias.alergias = alergias
            usuario.preferencias.gustos = gustos
        else:
            # Crear nuevas preferencias
            nueva_preferencia = Preferencia(
                usuario_id=usuario.id,
                dieta=dieta,
                alergias=alergias,
                gustos=gustos
            )
            db.session.add(nueva_preferencia)
        
        db.session.commit()
        
        print(f"✓ Preferencias actualizadas para usuario ID: {user_id}")
        print(f"  Dieta: {dieta}")
        print(f"  Alergias: {alergias}")
        print(f"  Gustos: {gustos}")
        
        return jsonify({
            'mensaje': 'Preferencias actualizadas exitosamente',
            'preferencias': {
                'dieta': dieta,
                'alergias': alergias,
                'gustos': gustos
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando preferencias: {str(e)}")
        return jsonify({'error': 'Ocurrió un error interno. Intente más tarde.'}), 500


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
            'email': correo_enmascarado,
           
            'link_recuperacion': link_recuperacion,
            'token': token,
            'expiracion': expiracion.isoformat()
        }), 200

    except Exception as e:
        print(f"Error procesando recuperación de contraseña: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@user_bp.route('/v1/usuarios/<int:id>', methods=['DELETE'])
@token_required
def eliminar_usuario(id):
    """
    Eliminar un usuario (soft delete - cambiar estado a inactivo)
    Solo el propio usuario puede eliminar su cuenta
    ---
    tags:
      - Usuarios
    security:
      - Bearer: []
    parameters:
      - in: path
        name: id
        required: true
        type: integer
        description: ID del usuario a eliminar
    responses:
      200:
        description: Usuario eliminado exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Usuario eliminado exitosamente"
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
                activo:
                  type: boolean
                  example: false
      404:
        description: Usuario no encontrado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuario no encontrado"
      403:
        description: No autorizado para eliminar este usuario
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Solo puedes eliminar tu propia cuenta"
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
        # Verificar que el usuario solo pueda eliminar su propia cuenta
        if request.current_user.id != id:
            return jsonify({'error': 'Solo puedes eliminar tu propia cuenta'}), 403
     
        usuario = Usuario.query.get(id)
        
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
       
        if not usuario.activo:
            return jsonify({'error': 'El usuario ya está inactivo'}), 400
        
        
        usuario.activo = False
        db.session.commit()
        
        print(f"✓ Usuario ID {id} marcado como inactivo por usuario ID {request.current_user.id}")
        
        return jsonify({
            'mensaje': 'Usuario eliminado exitosamente',
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'email': usuario.correo,
                'activo': usuario.activo
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error eliminando usuario: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
