from flask import Blueprint, request, jsonify
from modules.user.models import Usuario
from modules.recipe.recommendation_service import recommendation_service
import logging
from core.auth_middleware import token_required, optional_token
from core.role_middleware import owner_or_admin_required

logger = logging.getLogger("lazyfood.recipe")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

recipe_bp = Blueprint('recipe', __name__)


@recipe_bp.route('/v1/recetas/sugerencias', methods=['GET'])
@token_required
def obtener_sugerencias_recetas():
    """
    Obtener sugerencias de recetas personalizadas para el usuario autenticado
    ---
    tags:
      - Recetas
    security:
      - Bearer: []
    parameters:
      - name: cantidad
        in: query
        type: integer
        required: false
        description: Número máximo de recetas a devolver (1..20). Por defecto 5.
    responses:
      200:
        description: Lista de recetas sugeridas (sin pasos, pasos se generan on-demand)
        schema:
          type: array
          items:
            type: object
    400:
      description: Parámetro inválido
    401:
      description: No autenticado / token inválido
    404:
      description: Usuario sin inventario
    500:
      description: Error interno del servidor
    """
    try:
        user = request.current_user
        if not user:
            return jsonify({'error': 'Usuario no autenticado'}), 401

        from modules.inventory.models import Inventario
        if Inventario.query.filter_by(usuario_id=user.id).count() == 0:
            return jsonify({'error': 'El usuario no tiene ingredientes en el inventario. Escanea algunos ingredientes primero.'}), 404

        # leer query param 'cantidad' (opcional)
        cantidad_raw = request.args.get('cantidad', None)
        if cantidad_raw is not None:
            try:
                cantidad = int(cantidad_raw)
            except Exception:
                return jsonify({'error': 'Parámetro cantidad inválido'}), 400
        else:
            cantidad = 5  # valor por defecto si no se pasa

        if cantidad < 1 or cantidad > 20:
            return jsonify({'error': 'cantidad debe estar entre 1 y 20'}), 400

        recetas = recommendation_service.generar_recomendaciones(user.id, cantidad=cantidad)
        return jsonify(recetas), 200

    except Exception as e:
        logger.exception("Error obteniendo sugerencias de recetas")
        return jsonify({'error': 'Error interno del servidor'}), 500


@recipe_bp.route('/v1/recetas/sugerencias/historial', methods=['GET'])
@token_required
def obtener_historial_recomendaciones():
    """
    Obtener historial de recomendaciones del usuario autenticado
    ---
    tags:
      - Recetas
    security:
      - Bearer: []
    responses:
      200:
        description: Historial de recomendaciones
        schema:
          type: object
    401:
      description: No autenticado / token inválido
    500:
      description: Error interno del servidor
    """
    try:
        user = request.current_user
        if not user:
            return jsonify({'error': 'Usuario no autenticado'}), 401

        historial = recommendation_service.obtener_historial_recomendaciones(user.id)
        return jsonify({
            'usuario_id': user.id,
            'total_recomendaciones': len(historial),
            'recomendaciones': historial
        }), 200

    except Exception as e:
        logger.exception("Error obteniendo historial de recomendaciones")
        return jsonify({'error': 'Error interno del servidor'}), 500


@recipe_bp.route('/v1/recetas/<int:receta_id>', methods=['GET'])
@token_required
def obtener_detalle_receta(receta_id):
    """
    Obtener detalle completo de una receta
    ---
    tags:
      - Recetas
    security:
      - Bearer: []
    parameters:
      - name: receta_id
        in: path
        type: integer
        required: true
        description: ID de la receta
    responses:
      200:
        description: Detalle de la receta (incluye pasos si están guardados)
        schema:
          type: object
    404:
      description: Receta no encontrada
    500:
      description: Error interno del servidor
    """
    try:
        user = request.current_user
        if not user:
            return jsonify({'error': 'Usuario no autenticado'}), 401

        from modules.recipe.models import Receta, PasoReceta
        from modules.inventory.models import Inventario

        receta = Receta.query.get(receta_id)
        if not receta:
            return jsonify({'error': 'Receta no encontrada'}), 404

        pasos = PasoReceta.query.filter_by(receta_id=receta_id).order_by(PasoReceta.numero_paso).all()
        
        # Obtener ingredientes del inventario del usuario y generar con Gemini
        ingredientes_lista = []
        try:
            inventario_items = Inventario.query.filter_by(usuario_id=user.id).all()
            ingredientes_usuario = [item.ingrediente.nombre for item in inventario_items if getattr(item, "ingrediente", None)]
            
            preferencias = {}
            if getattr(user, "preferencias", None):
                try:
                    preferencias = user.preferencias.to_dict()
                except Exception:
                    preferencias = {
                        'dieta': getattr(user.preferencias, 'dieta', None),
                        'alergias': getattr(user.preferencias, 'alergias', []) or [],
                        'gustos': getattr(user.preferencias, 'gustos', []) or []
                    }
            
            # Usar Gemini para generar ingredientes especificos para esta receta
            from modules.ai.gemini_service import gemini_service
            
            logger.debug(f"Solicitando ingredientes específicos para '{receta.nombre}' a Gemini")
            ingredientes_lista = gemini_service.generar_ingredientes_receta(
                nombre_receta=receta.nombre,
                ingredientes_disponibles=ingredientes_usuario,
                preferencias=preferencias,
                nivel_cocina=user.nivel_cocina
            )
            
            logger.debug(f"Ingredientes generados: {len(ingredientes_lista)} para '{receta.nombre}'")
                
        except Exception as e:
            logger.exception(f"Error obteniendo ingredientes para receta {receta_id}")
            ingredientes_lista = []
        
        nivel_texto = 'Fácil' if receta.nivel_dificultad == 1 else ('Medio' if receta.nivel_dificultad == 2 else 'Difícil')
        
        respuesta = {
            'id': receta.id,
            'nombre': receta.nombre,
            'tiempo_preparacion': receta.tiempo_preparacion,
            'calorias': receta.calorias,
            'nivel_dificultad': nivel_texto,
            'emoji': receta.emoji,
            'ingredientes': ingredientes_lista,
            'pasos': [p.to_dict() for p in pasos]
        }
        return jsonify(respuesta), 200

    except Exception as e:
        logger.exception("Error obteniendo detalle de receta")
        return jsonify({'error': 'Error interno del servidor'}), 500


@recipe_bp.route('/v1/recetas/<int:receta_id>/pasos/generar', methods=['POST'])
@token_required
def generar_pasos_para_receta(receta_id):
    """
    Generar (on-demand) pasos detallados para una receta usando Gemini y guardar en DB.
    ---
    tags:
      - Recetas
    security:
      - Bearer: []
    parameters:
      - name: receta_id
        in: path
        required: true
        type: integer
        description: ID de la receta a la que generar pasos
    requestBody:
      required: false
      content:
        application/json:
          schema:
            type: object
            properties:
              ingredientes:
                type: array
                items:
                  type: object
                example:
                  - { "nombre": "Tomate", "cantidad": 2, "unidad": "unidades" }
    responses:
      200:
        description: Pasos generados y guardados
      400:
        description: Datos inválidos
      401:
        description: No autenticado / token inválido
      404:
        description: Receta o usuario no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json(silent=True) or {}
        ingredientes_override = data.get('ingredientes')

        try:
            pasos = recommendation_service.generar_y_guardar_pasos(
                receta_id=receta_id,
                usuario_id=request.current_user.id,
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