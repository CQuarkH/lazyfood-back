from flask import Blueprint, request, jsonify
from core.database import db
from core.auth_middleware import token_required
from core.role_middleware import owner_or_admin_required
from modules.user.models import Usuario
from modules.recipe.recommendation_service import recommendation_service

# Crear Blueprint para recetas
recipe_bp = Blueprint('recipe', __name__)


@recipe_bp.route('/v1/recetas/sugerencias/<int:user_id>', methods=['GET'])
@token_required
def obtener_sugerencias_recetas(user_id):
    """
    Obtener sugerencias de recetas personalizadas
    ---
    tags:
      - Recetas
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
    responses:
      200:
        description: Lista de recetas sugeridas
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                example: 15
                description: ID de la receta
              nombre:
                type: string
                example: "Ensalada de Tomate"
              tiempo:
                type: integer
                example: 10
                description: Tiempo de preparación en minutos
              calorias:
                type: integer
                example: 150
                description: Calorías por porción
              nivel:
                type: integer
                example: 1
                description: 1=fácil, 2=medio, 3=difícil
              razon:
                type: string
                example: "Coincide 85% con tus ingredientes y es apta para dieta vegana"
                description: Explicación de la recomendación
              ingredientes:
                type: array
                items:
                  type: object
                  properties:
                    nombre:
                      type: string
                      example: "tomate"
                    cantidad:
                      type: string
                      example: "2 unidades"
                    foto:
                      type: string
                      example: "https://cdn.lazyfood.com/ingredientes/tomate.jpg"
                    en_inventario:
                      type: boolean
                      example: true
              pasos:
                type: array
                items:
                  type: object
                  properties:
                    n:
                      type: integer
                      example: 1
                    instruccion:
                      type: string
                      example: "Lavar y cortar los tomates en rodajas"
                    timer:
                      type: integer
                      example: null
                      description: Temporizador en segundos (null si no aplica)
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

        # Verificar que el usuario tenga ingredientes en el inventario
        from modules.inventory.models import Inventario
        inventario_count = Inventario.query.filter_by(usuario_id=user_id).count()

        if inventario_count == 0:
            return jsonify({
                'error': 'El usuario no tiene ingredientes en el inventario. Escanea algunos ingredientes primero.'
            }), 404

        # Generar recomendaciones
        recetas = recommendation_service.generar_recomendaciones(user_id)

        # Formatear respuesta según contrato API
        respuesta_formateada = []
        for receta in recetas:
            receta_formateada = {
                'id': receta['id'],
                'nombre': receta['nombre'],
                'tiempo': receta['tiempo'],
                'calorias': receta['calorias'],
                'nivel': receta['nivel'],
                'razon': receta.get('razon', f"Coincide {receta['porcentaje_coincidencia']}% con tus ingredientes"),
                'ingredientes': receta['ingredientes'],
                'pasos': receta['pasos']
            }
            respuesta_formateada.append(receta_formateada)

        return jsonify(respuesta_formateada), 200

    except Exception as e:
        print(f"Error obteniendo sugerencias de recetas: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@recipe_bp.route('/v1/recetas/sugerencias/<int:user_id>/historial', methods=['GET'])
@token_required
def obtener_historial_recomendaciones(user_id):
    """
    Obtener historial de recomendaciones previas
    ---
    tags:
      - Recetas
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
    responses:
      200:
        description: Historial de recomendaciones
        schema:
          type: object
          properties:
            usuario_id:
              type: integer
              example: 1
            total_recomendaciones:
              type: integer
              example: 5
            recomendaciones:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 15
                  nombre:
                    type: string
                    example: "Ensalada de Tomate"
                  tiempo:
                    type: integer
                    example: 10
                  calorias:
                    type: integer
                    example: 150
                  nivel:
                    type: integer
                    example: 1
                  porcentaje_coincidencia:
                    type: number
                    format: float
                    example: 85.5
                  fecha:
                    type: string
                    format: date-time
                    example: "2024-01-15T10:30:00"
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

        # Obtener historial
        historial = recommendation_service.obtener_historial_recomendaciones(user_id)

        return jsonify({
            'usuario_id': user_id,
            'total_recomendaciones': len(historial),
            'recomendaciones': historial
        }), 200

    except Exception as e:
        print(f"Error obteniendo historial de recomendaciones: {str(e)}")
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
      - in: header
        name: Authorization
        required: true
        type: string
        description: Token JWT en formato "Bearer {token}"
      - name: receta_id
        in: path
        type: integer
        required: true
        description: ID de la receta
    responses:
      200:
        description: Detalle de la receta
        schema:
          type: object
          properties:
            id:
              type: integer
              example: 15
            nombre:
              type: string
              example: "Ensalada de Tomate"
            tiempo:
              type: integer
              example: 10
            calorias:
              type: integer
              example: 150
            nivel:
              type: integer
              example: 1
            imagen_url:
              type: string
              example: "https://cdn.lazyfood.com/recetas/ensalada_tomate.jpg"
            pasos:
              type: array
              items:
                type: object
                properties:
                  n:
                    type: integer
                    example: 1
                  instruccion:
                    type: string
                    example: "Lavar y cortar los tomates"
                  timer:
                    type: integer
                    example: null
      404:
        description: Receta no encontrada
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Receta no encontrada"
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
        from modules.recipe.models import Receta, PasoReceta

        receta = Receta.query.get(receta_id)
        if not receta:
            return jsonify({'error': 'Receta no encontrada'}), 404

        # Obtener pasos de la receta
        pasos = PasoReceta.query.filter_by(receta_id=receta_id) \
            .order_by(PasoReceta.numero_paso) \
            .all()

        respuesta = {
            'id': receta.id,
            'nombre': receta.nombre,
            'tiempo': receta.tiempo_preparacion,
            'calorias': receta.calorias,
            'nivel': receta.nivel_dificultad,
            'imagen_url': receta.imagen_url,
            'pasos': [paso.to_dict() for paso in pasos]
        }

        return jsonify(respuesta), 200

    except Exception as e:
        print(f"Error obteniendo detalle de receta: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500