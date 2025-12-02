from flask import Blueprint, request, jsonify
from core.auth_middleware import token_required
from modules.planner.planning_service import planning_service
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("lazyfood.planner.routes")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

planner_bp = Blueprint('planner', __name__)


@planner_bp.route('/v1/planificador/semana', methods=['GET'])
@token_required
def obtener_planificacion_semana():
    """
    Obtener planificación semanal del usuario autenticado
    ---
    tags:
      - Planificador
    security:
      - Bearer: []
    parameters:
      - name: fecha
        in: query
        type: string
        format: date
        required: false
        description: Fecha de inicio de la semana (YYYY-MM-DD). Si no se envía, se usa el lunes de la semana actual.
    responses:
      200:
        description: Planificación semanal encontrada
        schema:
          type: object
          properties:
            semana:
              type: string
              example: "2025-11-10"
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
                        nullable: true
                        example: 1
                      receta_nombre:
                        type: string
                        nullable: true
                        example: "Ensalada de Tomate"
                      es_sugerida:
                        type: boolean
                        example: true
                  almuerzo:
                    type: object
                  cena:
                    type: object
      400:
        description: Fecha con formato inválido
      401:
        description: No autenticado / token inválido
      500:
        description: Error interno del servidor
    """
    try:
        user = request.current_user
        if not user:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        usuario_id = user.id

        fecha_inicio = request.args.get('fecha')
        if not fecha_inicio:
            hoy = datetime.now()
            lunes = hoy - timedelta(days=hoy.weekday())
            fecha_inicio = lunes.strftime('%Y-%m-%d')

        try:
            datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}), 400

        plan = planning_service.obtener_planificacion(usuario_id, fecha_inicio)
        return jsonify(plan), 200

    except Exception as e:
        logger.exception("Error en obtener_planificacion_semana: %s", e)
        return jsonify({'error': 'Error interno del servidor'}), 500


@planner_bp.route('/v1/planificador/semana/sugerencias', methods=['POST'])
@token_required
def generar_planificacion_por_ia():
    """
    Generar planificación semanal por IA para el usuario autenticado
    ---
    tags:
      - Planificador
    security:
      - Bearer: []
    parameters:
      - name: fecha
        in: query
        type: string
        format: date
        required: false
        description: Fecha de inicio de la semana (YYYY-MM-DD). Opcional si se envía en el body.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              fecha:
                type: string
                format: date
                example: "2025-11-10"
                description: Fecha de inicio de la semana (lunes). Si no se envía, se usa el lunes de la semana actual.
    responses:
      200:
        description: Planificación generada por IA (IDs de recetas como enteros o null)
        schema:
          type: object
          properties:
            semana:
              type: string
              example: "2025-11-10"
            sugerencias:
              type: object
              additionalProperties:
                type: object
                properties:
                  desayuno:
                    type: integer
                    nullable: true
                    example: 1
                  almuerzo:
                    type: integer
                    nullable: true
                    example: 2
                  cena:
                    type: integer
                    nullable: true
                    example: 3
      400:
        description: Fecha con formato inválido o petición mal formada
      401:
        description: No autenticado / token inválido
      404:
        description: Usuario sin recetas sugeridas (necesita generar recomendaciones primero)
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Error interno del servidor
    """
    try:
        user = request.current_user
        if not user:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        usuario_id = user.id

        data = request.get_json(silent=True) or {}
        fecha = data.get('fecha') or request.args.get('fecha')
        if not fecha:
            hoy = datetime.now()
            lunes = hoy - timedelta(days=hoy.weekday())
            fecha = lunes.strftime('%Y-%m-%d')

        try:
            datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}), 400

        result = planning_service.generar_sugerencias_planificacion(usuario_id, fecha)

        if isinstance(result, dict) and result.get('error'):
            codigo = result.get('codigo')
            if codigo == 'no_recetas_usuario':
                return jsonify({'error': result.get('error')}), 404
            elif codigo == 'usuario_no_encontrado' or codigo == 'no_recetas_validas':
                return jsonify({'error': result.get('error')}), 400
            else:
                return jsonify({'error': result.get('error')}), 400

        return jsonify(result), 200

    except Exception as e:
        logger.exception("Error en generar_planificacion_por_ia: %s", e)
        return jsonify({'error': 'Error interno del servidor'}), 500
