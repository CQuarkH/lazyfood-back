from flask import Blueprint, request, jsonify
from core.database import db
from core.auth_middleware import token_required
from core.role_middleware import owner_or_admin_required
from modules.user.models import Usuario
from modules.planner.planning_service import planning_service
from datetime import datetime, timedelta

# Crear Blueprint para planificador
planner_bp = Blueprint('planner', __name__)


@planner_bp.route('/v1/planificador/semana/<int:user_id>', methods=['PUT'])
@token_required
def crear_actualizar_planificacion(user_id):
    """
    Crear o actualizar planificación semanal
    ---
    tags:
      - Planificador
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Token JWT en formato "Bearer {token}"
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID del usuario
      - in: body
        name: body
        schema:
          type: object
          required:
            - semana
            - menus
          properties:
            semana:
              type: string
              format: date
              example: "2024-01-15"
              description: Fecha de inicio de la semana (lunes)
            menus:
              type: object
              description: Menús organizados por fecha y tipo de comida
              additionalProperties:
                type: object
                properties:
                  desayuno:
                    type: integer
                    example: 1
                    description: ID de la receta para desayuno
                  almuerzo:
                    type: integer
                    example: 2
                    description: ID de la receta para almuerzo
                  cena:
                    type: integer
                    example: 3
                    description: ID de la receta para cena
    responses:
      200:
        description: Planificación guardada exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Planificación semanal guardada correctamente"
            semana:
              type: string
              example: "2024-01-15"
            menus:
              type: object
              additionalProperties:
                type: object
                properties:
                  desayuno:
                    type: integer
                    example: 1
                  almuerzo:
                    type: integer
                    example: 2
                  cena:
                    type: integer
                    example: 3
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
              example: "Error interno del servidor"
    """
    try:
        # Verificar que el usuario existe
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Obtener datos del cuerpo
        data = request.get_json()
        if not data or 'semana' not in data or 'menus' not in data:
            return jsonify({'error': 'Datos inválidos, se esperaba semana y menus'}), 400

        semana = data['semana']
        menus = data['menus']

        # Validar formato de fecha
        try:
            datetime.strptime(semana, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}), 400

        # Validar estructura de menus
        if not isinstance(menus, dict):
            return jsonify({'error': 'Menus debe ser un objeto JSON'}), 400

        # Guardar planificación
        planning_service.guardar_planificacion(user_id, {
            'semana': semana,
            'menus': menus
        })

        return jsonify({
            'mensaje': 'Planificación semanal guardada correctamente',
            'semana': semana,
            'menus': menus
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error guardando planificación: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@planner_bp.route('/v1/planificador/semana/<int:user_id>', methods=['GET'])
@token_required
def obtener_planificacion(user_id):
    """
    Obtener planificación semanal
    ---
    tags:
      - Planificador
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Token JWT en formato "Bearer {token}"
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID del usuario
      - name: fecha
        in: query
        type: string
        format: date
        description: Fecha de inicio de la semana (YYYY-MM-DD). Por defecto, semana actual.
    responses:
      200:
        description: Planificación semanal
        schema:
          type: object
          properties:
            semana:
              type: string
              example: "2024-01-15"
            menus:
              type: object
              additionalProperties:
                type: object
                properties:
                  desayuno:
                    type: object
                    properties:
                      receta_id:
                        type: integer
                        example: 1
                      receta_nombre:
                        type: string
                        example: "Ensalada de Tomate"
                      es_sugerida:
                        type: boolean
                        example: false
                  almuerzo:
                    type: object
                    properties:
                      receta_id:
                        type: integer
                        example: 2
                      receta_nombre:
                        type: string
                        example: "Pasta con Tomate"
                      es_sugerida:
                        type: boolean
                        example: false
                  cena:
                    type: object
                    properties:
                      receta_id:
                        type: integer
                        example: 3
                      receta_nombre:
                        type: string
                        example: "Huevos Revueltos"
                      es_sugerida:
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
        # Verificar que el usuario existe
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Obtener parámetro de fecha (opcional, por defecto semana actual)
        fecha_inicio = request.args.get('fecha')
        if not fecha_inicio:
            # Calcular lunes de la semana actual
            hoy = datetime.now()
            lunes = hoy - timedelta(days=hoy.weekday())
            fecha_inicio = lunes.strftime('%Y-%m-%d')

        # Validar formato de fecha
        try:
            datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}), 400

        # Obtener planificación
        planificacion = planning_service.obtener_planificacion(user_id, fecha_inicio)

        return jsonify(planificacion), 200

    except Exception as e:
        print(f"Error obteniendo planificación: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@planner_bp.route('/v1/planificador/semana/sugerencias/<int:user_id>', methods=['GET'])
@token_required
def obtener_sugerencias_planificacion(user_id):
    """
    Obtener sugerencias de planificación semanal generadas por IA
    ---
    tags:
      - Planificador
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Token JWT en formato "Bearer {token}"
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID del usuario
      - name: fecha
        in: query
        type: string
        format: date
        description: Fecha de inicio de la semana (YYYY-MM-DD). Por defecto, semana actual.
    responses:
      200:
        description: Sugerencias de planificación generadas por IA
        schema:
          type: object
          properties:
            semana:
              type: string
              example: "2024-01-15"
            sugerencias:
              type: object
              additionalProperties:
                type: object
                properties:
                  desayuno:
                    type: integer
                    example: 1
                    description: ID de receta sugerida para desayuno
                  almuerzo:
                    type: integer
                    example: 2
                    description: ID de receta sugerida para almuerzo
                  cena:
                    type: integer
                    example: 3
                    description: ID de receta sugerida para cena
      404:
        description: Usuario no encontrado o sin ingredientes
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
        # Verificar que el usuario existe
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Obtener parámetro de fecha (opcional, por defecto semana actual)
        fecha_inicio = request.args.get('fecha')
        if not fecha_inicio:
            # Calcular lunes de la semana actual
            hoy = datetime.now()
            lunes = hoy - timedelta(days=hoy.weekday())
            fecha_inicio = lunes.strftime('%Y-%m-%d')

        # Validar formato de fecha
        try:
            datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}), 400

        # Verificar que el usuario tenga ingredientes en el inventario
        from modules.inventory.models import Inventario
        inventario_count = Inventario.query.filter_by(usuario_id=user_id).count()

        if inventario_count == 0:
            return jsonify({
                'error': 'El usuario no tiene ingredientes en el inventario. Escanea algunos ingredientes primero.'
            }), 404

        # Generar sugerencias
        sugerencias = planning_service.generar_sugerencias_planificacion(user_id, fecha_inicio)

        return jsonify(sugerencias), 200

    except Exception as e:
        print(f"Error obteniendo sugerencias de planificación: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500