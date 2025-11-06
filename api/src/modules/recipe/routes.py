# api/src/modules/recipe/routes.py
from flask import Blueprint, request, jsonify
from modules.user.models import Usuario
from modules.recipe.recommendation_service import recommendation_service
import logging

logger = logging.getLogger("lazyfood.recipe")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

recipe_bp = Blueprint('recipe', __name__)


@recipe_bp.route('/v1/recetas/sugerencias/<int:user_id>', methods=['GET'])
def obtener_sugerencias_recetas(user_id):
    """
    Obtener sugerencias de recetas personalizadas
    ---
    tags:
      - Recetas
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID del usuario
    responses:
      200:
        description: Lista de recetas sugeridas (sin pasos, pasos se generan on-demand)
      404:
        description: Usuario no encontrado o sin ingredientes
      500:
        description: Error interno del servidor
    """
    try:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        from modules.inventory.models import Inventario
        if Inventario.query.filter_by(usuario_id=user_id).count() == 0:
            return jsonify({'error': 'El usuario no tiene ingredientes en el inventario. Escanea algunos ingredientes primero.'}), 404

        recetas = recommendation_service.generar_recomendaciones(user_id)
        return jsonify(recetas), 200

    except Exception as e:
        logger.exception("Error obteniendo sugerencias de recetas")
        return jsonify({'error': 'Error interno del servidor'}), 500


@recipe_bp.route('/v1/recetas/sugerencias/<int:user_id>/historial', methods=['GET'])
def obtener_historial_recomendaciones(user_id):
    """
    Obtener historial de recomendaciones previas
    ---
    tags:
      - Recetas
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID del usuario
    responses:
      200:
        description: Historial de recomendaciones
      404:
        description: Usuario no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        historial = recommendation_service.obtener_historial_recomendaciones(user_id)
        return jsonify({
            'usuario_id': user_id,
            'total_recomendaciones': len(historial),
            'recomendaciones': historial
        }), 200

    except Exception as e:
        logger.exception("Error obteniendo historial de recomendaciones")
        return jsonify({'error': 'Error interno del servidor'}), 500


@recipe_bp.route('/v1/recetas/<int:receta_id>', methods=['GET'])
def obtener_detalle_receta(receta_id):
    """
    Obtener detalle completo de una receta
    ---
    tags:
      - Recetas
    parameters:
      - name: receta_id
        in: path
        type: integer
        required: true
        description: ID de la receta
    responses:
      200:
        description: Detalle de la receta (incluye pasos si están guardados)
      404:
        description: Receta no encontrada
      500:
        description: Error interno del servidor
    """
    try:
        from modules.recipe.models import Receta, PasoReceta

        receta = Receta.query.get(receta_id)
        if not receta:
            return jsonify({'error': 'Receta no encontrada'}), 404

        pasos = PasoReceta.query.filter_by(receta_id=receta_id).order_by(PasoReceta.numero_paso).all()
        respuesta = {
            'id': receta.id,
            'nombre': receta.nombre,
            'tiempo': receta.tiempo_preparacion,
            'calorias': receta.calorias,
            'nivel': receta.nivel_dificultad,
            'emoji': receta.emoji,
            'pasos': [p.to_dict() for p in pasos]
        }
        return jsonify(respuesta), 200

    except Exception as e:
        logger.exception("Error obteniendo detalle de receta")
        return jsonify({'error': 'Error interno del servidor'}), 500


@recipe_bp.route('/v1/recetas/<int:receta_id>/pasos/generar', methods=['POST'])
def generar_pasos_para_receta(receta_id):
    """
    Generar (on-demand) pasos detallados para una receta usando Gemini y guardar en DB.
    ---
    tags:
      - Recetas
    parameters:
      - name: receta_id
        in: path
        required: true
        type: integer
        description: ID de la receta a la que generar pasos
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            usuario_id:
              type: integer
              description: ID de usuario para tomar preferencias / inventario
    responses:
      200:
        description: Pasos generados y guardados
      400:
        description: Datos inválidos
      404:
        description: Receta o usuario no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json(silent=True) or {}
        usuario_id = data.get('usuario_id')
        ingredientes_override = data.get('ingredientes')

        try:
            pasos = recommendation_service.generar_y_guardar_pasos(
                receta_id=receta_id,
                usuario_id=usuario_id,
                ingredientes_override=ingredientes_override
            )
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 404
        except Exception as e:
            logger.exception("Error generando y guardando pasos")
            return jsonify({'error': 'Error generando pasos'}), 500

        if pasos is None:
            return jsonify({'error': 'No se pudieron generar pasos'}), 500

        return jsonify({'receta_id': receta_id, 'pasos': pasos}), 200

    except Exception as e:
        logger.exception("Error en endpoint generar_pasos_para_receta")
        return jsonify({'error': 'Error interno del servidor'}), 500
