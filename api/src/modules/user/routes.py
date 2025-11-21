from flask import Blueprint, jsonify, request, render_template_string
from core.database import db
from modules.user.models import Usuario, Preferencia
from core.auth_middleware import token_required
from core.role_middleware import role_required, admin_required, owner_or_admin_required
from core.email_service import EmailService
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


def validar_nivel_cocina(nivel):
    """
    Valida el nivel de cocina del usuario
    Returns: (bool, str) - (es_valido, mensaje_error)
    """
    if nivel is None:
        return False, "El nivel de cocina es obligatorio"
    
    try:
        nivel_int = int(nivel)
        if nivel_int not in [1, 2, 3]:
            return False, "El nivel de cocina debe ser 1, 2 o 3"
        return True, ""
    except (ValueError, TypeError):
        return False, "El nivel de cocina debe ser un número entero"


def validar_metas_nutricionales(meta):
    """
    Valida las metas nutricionales del usuario
    Returns: (bool, str) - (es_valido, mensaje_error)
    """
    if not meta:
        return False, "Las metas nutricionales son obligatorias"
    
    metas_permitidas = [
        "ninguna",
        "Mantener salud general",
        "Bajar de peso",
        "Aumentar masa muscular",
        "Mejorar energía",
        "Cocinar más en casa",
        "Ahorrar dinero"
    ]
    
    if meta not in metas_permitidas:
        return False, f"Meta nutricional no válida. Opciones: {', '.join(metas_permitidas)}"
    
    return True, ""


def validar_alergias(alergias):
    """
    Valida que las alergias sean de las permitidas
    Returns: (bool, str, list) - (es_valido, mensaje_error, alergias_invalidas)
    """
    alergias_permitidas = [
        "gluten",
        "lacteos",
        "frutos secos",
        "mariscos",
        "huevo",
        "soja"
    ]
    
    if not isinstance(alergias, list):
        return False, "Las alergias deben ser una lista", []
    
    # Normalizar alergias a minúsculas para comparación
    alergias_normalizadas = [alergia.strip().lower() for alergia in alergias]
    alergias_invalidas = [alergia for alergia in alergias_normalizadas if alergia not in alergias_permitidas]
    
    if alergias_invalidas:
        return False, f"Alergias no válidas: {', '.join(alergias_invalidas)}. Opciones permitidas: {', '.join(alergias_permitidas)}", alergias_invalidas
    
    return True, "", []


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
            nivel_cocina:
              type: string
              example: "1"
              description: (Opcional) Nivel de cocina (1=principiante, 2=intermedio, 3=avanzado). Por defecto 1
            metas_nutricionales:
              type: string
              example: "Bajar de peso"
              description: |
                (Opcional) Metas nutricionales del usuario. Opciones permitidas:
                - ninguna (valor por defecto)
                - Mantener salud general
                - Bajar de peso
                - Aumentar masa muscular
                - Mejorar energía
                - Cocinar más en casa
                - Ahorrar dinero
            pais:
              type: string
              example: "Chile"
              description: (Opcional) País del usuario
            preferencias:
              type: object
              description: (Opcional) Preferencias alimentarias del usuario
              properties:
                dieta:
                  type: string
                  example: "vegano"
                  description: Tipo de dieta (vegano, vegetariano, keto, etc.)
                alergias:
                  type: array
                  items:
                    type: string
                  example: ["gluten", "lacteos"]
                  description: |
                    Lista de alergias alimentarias (opcional)
                    Alergias permitidas: gluten, lacteos, frutos secos, mariscos, huevo, soja
                gustos:
                  type: array
                  items:
                    type: string
                  example: ["pasta", "frutas"]
                  description: Lista de preferencias alimentarias (opcional)
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
        nivel_cocina = data.get('nivel_cocina')
        metas_nutricionales = data.get('metas_nutricionales', 'ninguna').strip() if data.get('metas_nutricionales') else 'ninguna'
        pais = data.get('pais', '').strip() if data.get('pais') else None
        preferencias_data = data.get('preferencias')

        # Validar que los campos obligatorios no estén vacíos
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
        
        # Validar nivel de cocina si se proporciona
        if nivel_cocina is not None:
            nivel_valido, error_nivel = validar_nivel_cocina(nivel_cocina)
            if not nivel_valido:
                return jsonify({'error': 'Datos inválidos'}), 400
        else:
            nivel_cocina = 1  # Valor por defecto
        
        # Validar metas nutricionales si se proporciona
        if metas_nutricionales:
            metas_validas, error_metas = validar_metas_nutricionales(metas_nutricionales)
            if not metas_validas:
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
            nivel_cocina=int(nivel_cocina),
            metas_nutricionales=metas_nutricionales,
            activo=True
        )

        # Guardar en la base de datos
        db.session.add(nuevo_usuario)
        db.session.flush()  # Para obtener el ID del usuario antes de commit

        # Crear preferencias si se proporcionan
        if preferencias_data and isinstance(preferencias_data, dict):
            dieta = preferencias_data.get('dieta')
            gustos = preferencias_data.get('gustos', [])  # Gustos es opcional
            alergias = preferencias_data.get('alergias', [])  # Alergias es opcional
            
            # Validar que dieta esté presente si se proporcionan preferencias
            if not dieta:
                return jsonify({'error': 'Datos inválidos'}), 400
            
            # Validar que gustos sea una lista (si se proporciona)
            if gustos and not isinstance(gustos, list):
                return jsonify({'error': 'Datos inválidos'}), 400
            
            # Validar alergias (si se proporcionan)
            if alergias:
                if not isinstance(alergias, list):
                    return jsonify({'error': 'Datos inválidos'}), 400
                
                # Validar que las alergias sean de las permitidas
                alergias_validas, error_alergias, alergias_invalidas = validar_alergias(alergias)
                if not alergias_validas:
                    return jsonify({'error': error_alergias}), 400
            
            nueva_preferencia = Preferencia(
                usuario_id=nuevo_usuario.id,
                dieta=dieta,
                alergias=alergias if alergias else [],
                gustos=gustos if gustos else []
            )
            db.session.add(nueva_preferencia)

        db.session.commit()

        print(f"✓ Usuario registrado exitosamente: {correo}")
        print(f"  Nombre: {nombre}")
        print(f"  ID: {nuevo_usuario.id}")
        print(f"  País: {pais}")
        print(f"  Nivel cocina: {nivel_cocina}")
        print(f"  Metas nutricionales: {metas_nutricionales}")
        if preferencias_data:
            print(f"  Preferencias: {preferencias_data}")

        # Preparar respuesta con solo los datos solicitados
        response_data = {
            'mensaje': 'Usuario creado correctamente',
            'id': nuevo_usuario.id,
            'nombre': nuevo_usuario.nombre,
            'email': nuevo_usuario.correo,
            'pais': nuevo_usuario.pais,
            'nivel_cocina': nuevo_usuario.nivel_cocina,
            'metas_nutricionales': nuevo_usuario.metas_nutricionales,
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
    Actualizar las preferencias alimentarias, nivel de cocina y metas nutricionales de un usuario
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
            nivel_cocina:
              type: integer
              example: 2
              description: Nivel de cocina (1=principiante, 2=intermedio, 3=avanzado)
            metas_nutricionales:
              type: string
              example: "Bajar de peso"
              description: Metas nutricionales del usuario (ninguna, Mantener salud general, Bajar de peso, Aumentar masa muscular, Mejorar energía, Cocinar más en casa, Ahorrar dinero)
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
            usuario:
              type: object
              properties:
                nivel_cocina:
                  type: integer
                  example: 2
                metas_nutricionales:
                  type: string
                  example: "Bajar de peso"
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
        
        # Actualizar nivel de cocina si se proporciona
        nivel_cocina = data.get('nivel_cocina')
        if nivel_cocina is not None:
            es_valido, mensaje_error = validar_nivel_cocina(nivel_cocina)
            if not es_valido:
                return jsonify({'error': mensaje_error}), 400
            usuario.nivel_cocina = int(nivel_cocina)
        
        # Actualizar metas nutricionales si se proporciona
        metas_nutricionales = data.get('metas_nutricionales')
        if metas_nutricionales is not None:
            es_valido, mensaje_error = validar_metas_nutricionales(metas_nutricionales)
            if not es_valido:
                return jsonify({'error': mensaje_error}), 400
            usuario.metas_nutricionales = metas_nutricionales
        
        # Verificar si el usuario ya tiene preferencias
        if usuario.preferencias:
            # Actualizar preferencias existentes
            if dieta is not None:
                usuario.preferencias.dieta = dieta
            if alergias:
                usuario.preferencias.alergias = alergias
            if gustos:
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
        if nivel_cocina is not None:
            print(f"  Nivel de cocina: {nivel_cocina}")
        if metas_nutricionales is not None:
            print(f"  Metas nutricionales: {metas_nutricionales}")
        
        response_data = {
            'mensaje': 'Preferencias actualizadas exitosamente',
            'preferencias': {
                'dieta': usuario.preferencias.dieta if usuario.preferencias else None,
                'alergias': usuario.preferencias.alergias if usuario.preferencias else [],
                'gustos': usuario.preferencias.gustos if usuario.preferencias else []
            },
            'usuario': {
                'nivel_cocina': usuario.nivel_cocina,
                'metas_nutricionales': usuario.metas_nutricionales
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando preferencias: {str(e)}")
        return jsonify({'error': 'Ocurrió un error interno. Intente más tarde.'}), 500


@user_bp.route('/v1/usuarios/recuperar-password', methods=['POST'])
def recuperar_password():
    """
    Solicitar recuperación de contraseña por email
    ---
    tags:
      - Usuarios
    parameters:
      - in: body
        name: body
        required: true
        description: Email del usuario
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: "usuario@ejemplo.com"
              description: Email del usuario que solicita recuperar contraseña
    responses:
      200:
        description: Solicitud de recuperación procesada exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Si el correo existe, recibirás un enlace de recuperación"
            correo:
              type: string
              example: "usu***@ejemplo.com"
              description: Correo enmascarado (solo si el usuario existe)
      400:
        description: Email faltante o inválido
        schema:
          type: object
          properties:
            error:
              type: string
              example: "El email es obligatorio"
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
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'El email es obligatorio'}), 400
        
        # Validar formato de email
        email_valido, error_email = validar_email(email)
        if not email_valido:
            return jsonify({'error': 'Formato de email inválido'}), 400
        
        # Buscar usuario por email
        usuario = Usuario.query.filter_by(correo=email).first()
        
        # Por seguridad, siempre retornamos el mismo mensaje (para no revelar si el email existe)
        if not usuario:
            return jsonify({
                'mensaje': 'Si el correo existe, recibirás un enlace de recuperación'
            }), 200
        
        # Generar token de recuperación
        token = secrets.token_urlsafe(32)
        expiracion = datetime.utcnow() + timedelta(hours=1)
        
        # Guardar token en la base de datos
        usuario.reset_token = token
        usuario.reset_token_expiration = expiracion
        db.session.commit()
        
        # Construir link de recuperación
        link_recuperacion = f"http://localhost:5000/reset-password?token={token}"
        
        # Enviar email
        email_enviado, mensaje = EmailService.send_password_reset_email(
            to_email=usuario.correo,
            reset_link=link_recuperacion,
            user_name=usuario.nombre
        )
        
        # Enmascarar email para la respuesta
        partes = usuario.correo.split('@')
        if len(partes[0]) > 3:
            correo_enmascarado = f"{partes[0][:3]}***@{partes[1]}"
        else:
            correo_enmascarado = f"{partes[0][0]}***@{partes[1]}"
        
        print(f"✓ Token de recuperación generado para: {usuario.correo}")
        print(f"  Usuario: {usuario.nombre}")
        print(f"  Link: {link_recuperacion}")
        print(f"  Expira: {expiracion}")
        print(f"  Email enviado: {email_enviado}")
        
        return jsonify({
            'mensaje': 'Si el correo existe, recibirás un enlace de recuperación',
            'correo': correo_enmascarado
        }), 200
        
    except Exception as e:
        db.session.rollback()
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


@user_bp.route('/reset-password', methods=['GET'])
def reset_password_page():
    """
    Página HTML para restablecer contraseña
    ---
    tags:
      - Usuarios
    parameters:
      - in: query
        name: token
        type: string
        required: true
        description: Token de recuperación de contraseña
    responses:
      200:
        description: Página HTML para restablecer contraseña
        content:
          text/html:
            schema:
              type: string
    """
    token = request.args.get('token', '')
    
    html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restablecer Contraseña - LazyFood</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #A96224 0%, #8B4E1C 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 450px;
            width: 100%;
            padding: 40px;
            animation: slideIn 0.5s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 15px;
            background-color: #A96224;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            font-weight: bold;
            color: white;
        }
        
        h1 {
            color: #333;
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        input[type="password"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        input[type="password"]:focus {
            outline: none;
            border-color: #A96224;
            box-shadow: 0 0 0 3px rgba(169, 98, 36, 0.1);
        }
        
        .password-requirements {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            font-size: 12px;
        }
        
        .password-requirements h4 {
            color: #333;
            margin-bottom: 10px;
            font-size: 13px;
        }
        
        .requirement {
            color: #666;
            margin: 5px 0;
            display: flex;
            align-items: center;
        }
        
        .requirement::before {
            content: "•";
            color: #A96224;
            font-weight: bold;
            margin-right: 8px;
        }
        
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #A96224 0%, #8B4E1C 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(169, 98, 36, 0.3);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .alert {
            padding: 12px 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #A96224;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .success-message {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .success-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">LF</div>
            <h1>Restablecer Contraseña</h1>
            <p class="subtitle">Ingresa tu nueva contraseña</p>
        </div>
        
        <div id="alert" class="alert"></div>
        
        <form id="resetForm">
            <div class="form-group">
                <label for="password">Nueva Contraseña</label>
                <input 
                    type="password" 
                    id="password" 
                    name="password" 
                    placeholder="Ingresa tu nueva contraseña"
                    required
                >
            </div>
            
            <div class="form-group">
                <label for="confirmPassword">Confirmar Contraseña</label>
                <input 
                    type="password" 
                    id="confirmPassword" 
                    name="confirmPassword" 
                    placeholder="Confirma tu nueva contraseña"
                    required
                >
            </div>
            
            <div class="password-requirements">
                <h4>La contraseña debe cumplir:</h4>
                <div class="requirement">Mínimo 8 caracteres</div>
                <div class="requirement">Máximo 128 caracteres</div>
            </div>
            
            <button type="submit" id="submitBtn">Restablecer Contraseña</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 10px; color: #666;">Procesando...</p>
        </div>
        
        <div class="success-message" id="successMessage">
            <div class="success-icon">✅</div>
            <h2>¡Contraseña Actualizada!</h2>
            <p style="color: #666; margin-top: 10px;">Tu contraseña ha sido cambiada exitosamente.</p>
            <p style="color: #666; margin-top: 5px;">Ya puedes cerrar esta página.</p>
        </div>
    </div>
    
    <script>
        const token = '{{ token }}';
        const form = document.getElementById('resetForm');
        const alertDiv = document.getElementById('alert');
        const loading = document.getElementById('loading');
        const successMessage = document.getElementById('successMessage');
        const submitBtn = document.getElementById('submitBtn');
        
        function showAlert(message, type) {
            alertDiv.textContent = message;
            alertDiv.className = 'alert alert-' + type;
            alertDiv.style.display = 'block';
            
            setTimeout(() => {
                alertDiv.style.display = 'none';
            }, 5000);
        }
        
        function validatePassword(password) {
            if (password.length < 8) {
                return 'La contraseña debe tener al menos 8 caracteres';
            }
            if (password.length > 128) {
                return 'La contraseña no debe exceder 128 caracteres';
            }
            return null;
        }
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            // Validaciones
            if (!password || !confirmPassword) {
                showAlert('Por favor completa todos los campos', 'error');
                return;
            }
            
            const passwordError = validatePassword(password);
            if (passwordError) {
                showAlert(passwordError, 'error');
                return;
            }
            
            if (password !== confirmPassword) {
                showAlert('Las contraseñas no coinciden', 'error');
                return;
            }
            
            // Mostrar loading
            form.style.display = 'none';
            loading.style.display = 'block';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/v1/usuarios/cambiar-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        token: token,
                        new_password: password
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Mostrar mensaje de éxito
                    loading.style.display = 'none';
                    successMessage.style.display = 'block';
                } else {
                    throw new Error(data.error || 'Error al cambiar la contraseña');
                }
                
            } catch (error) {
                loading.style.display = 'none';
                form.style.display = 'block';
                submitBtn.disabled = false;
                showAlert(error.message, 'error');
            }
        });
    </script>
</body>
</html>
    """
    
    return render_template_string(html_template, token=token)


@user_bp.route('/v1/usuarios/cambiar-password', methods=['POST'])
def cambiar_password():
    """
    Cambiar contraseña usando token de recuperación
    ---
    tags:
      - Usuarios
    parameters:
      - in: body
        name: body
        required: true
        description: Token y nueva contraseña
        schema:
          type: object
          required:
            - token
            - new_password
          properties:
            token:
              type: string
              example: "abc123xyz456def789..."
              description: Token de recuperación recibido por email
            new_password:
              type: string
              format: password
              example: "NuevaPassword123"
              description: Nueva contraseña (mínimo 8 caracteres)
    responses:
      200:
        description: Contraseña cambiada exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Contraseña actualizada exitosamente"
      400:
        description: Datos inválidos o token expirado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Token inválido o expirado"
      404:
        description: Token no encontrado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Token no válido"
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
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        token = data.get('token', '').strip()
        new_password = data.get('new_password', '')
        
        if not token or not new_password:
            return jsonify({'error': 'Token y contraseña son obligatorios'}), 400
        
        # Validar nueva contraseña
        password_valida, error_password = validar_password_segura(new_password)
        if not password_valida:
            return jsonify({'error': error_password}), 400
        
        # Buscar usuario por token
        usuario = Usuario.query.filter_by(reset_token=token).first()
        
        if not usuario:
            return jsonify({'error': 'Token no válido'}), 404
        
        # Verificar que el token no haya expirado
        if not usuario.reset_token_expiration or datetime.utcnow() > usuario.reset_token_expiration:
            return jsonify({'error': 'Token inválido o expirado'}), 400
        
        # Hashear la nueva contraseña
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Actualizar contraseña y limpiar token
        usuario.password = password_hash
        usuario.reset_token = None
        usuario.reset_token_expiration = None
        db.session.commit()
        
        # Enviar email de confirmación
        EmailService.send_password_changed_confirmation(
            to_email=usuario.correo,
            user_name=usuario.nombre
        )
        
        print(f"✓ Contraseña actualizada para usuario: {usuario.correo}")
        
        return jsonify({
            'mensaje': 'Contraseña actualizada exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error cambiando contraseña: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
