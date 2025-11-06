# modules/inventory/routes.py
from flask import Blueprint, request, jsonify
from core.database import db
from sqlalchemy.exc import IntegrityError
from modules.user.models import Usuario
from modules.inventory.models import Ingrediente, Inventario

# Crear Blueprint para inventario
inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/v1/ingredientes', methods=['PUT'])
def actualizar_inventario():
    """
    Actualizar inventario de usuario
    ---
    tags:
      - Inventario
    parameters:
      - name: userId
        in: query
        type: integer
        required: true
        description: ID del usuario
      - in: body
        name: body
        schema:
          type: object
          required:
            - ingredientes
          properties:
            ingredientes:
              type: array
              description: Lista de ingredientes detectados (DetectedIngredient)
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: "tomate"
                    description: Identificador/clave del ingrediente (opcional)
                  name:
                    type: string
                    example: "tomate"
                    description: Nombre del ingrediente
                  emoji:
                    type: string
                    example: "🍅"
                    description: Emoji representativo del ingrediente (opcional)
                  category:
                    type: string
                    example: "verdura"
                    description: Categoría del ingrediente (opcional)
                  quantity:
                    type: number
                    format: float
                    example: 3
                    description: Cantidad detectada
                  unit:
                    type: string
                    example: "unidades"
                    description: Unidad de la cantidad
                  confidence:
                    type: number
                    format: float
                    example: 0.95
                    description: Nivel de confianza de la detección (0-1)
                  bounding_box:
                    type: object
                    properties:
                      x:
                        type: number
                        example: 0.25
                      y:
                        type: number
                        example: 0.3
                      width:
                        type: number
                        example: 0.2
                      height:
                        type: number
                        example: 0.25
                    description: Bounding box normalizada (0-1), opcional
    responses:
      200:
        description: Inventario actualizado exitosamente
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Inventario del usuario actualizado."
            detalles:
              type: array
              items:
                type: object
                properties:
                  ingrediente:
                    type: string
                    example: "Tomate"
                  accion:
                    type: string
                    example: "agregado"
                  cantidad:
                    type: number
                    example: 3
                  confianza:
                    type: number
                    example: 0.95
                  ingrediente_id:
                    type: integer
                    example: 1
                  emoji:
                    type: string
                    example: "🍅"
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
        # Obtener parámetros y validar userId
        user_id_raw = request.args.get('userId')
        if not user_id_raw:
            return jsonify({'error': 'Se requiere el parámetro userId'}), 400

        try:
            user_id = int(user_id_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'userId inválido'}), 400

        # Verificar que el usuario existe
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Obtener y validar datos del body
        data = request.get_json(silent=True)
        if not data or 'ingredientes' not in data:
            return jsonify({'error': 'Datos inválidos, se esperaba una lista de ingredientes'}), 400

        ingredientes_data = data['ingredientes']
        if not isinstance(ingredientes_data, list):
            return jsonify({'error': 'Campo ingredientes debe ser un arreglo'}), 400

        # Validar estructura mínima de cada ingrediente
        for ingrediente_data in ingredientes_data:
            if not isinstance(ingrediente_data, dict):
                return jsonify({'error': 'Cada ingrediente debe ser un objeto JSON'}), 400
            if not ('name' in ingrediente_data or 'id' in ingrediente_data):
                return jsonify({'error': 'Cada ingrediente debe tener al menos "name" o "id"'}), 400
            if 'quantity' not in ingrediente_data:
                return jsonify({'error': 'Cada ingrediente debe tener "quantity"'}), 400

        resultados = []
        for ingrediente_data in ingredientes_data:
            resultado = _procesar_ingrediente(user_id, ingrediente_data)
            resultados.append(resultado)

        # Commit global
        db.session.commit()

        return jsonify({
            'mensaje': 'Inventario del usuario actualizado.',
            'detalles': resultados
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando inventario: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


def _procesar_ingrediente(usuario_id, ingrediente_data):
    """
    Procesa un ingrediente individual: lo busca o crea, y actualiza el inventario.

    Se espera ingrediente_data con la forma (DetectedIngredient):
    {
      "id": "tomate",              # opcional
      "name": "tomate",
      "emoji": "🍅",               # opcional
      "category": "verdura",       # opcional
      "quantity": 2,
      "unit": "unidades",
      "confidence": 0.95,
      "bounding_box": {"x":0.25,"y":0.3,"width":0.2,"height":0.25}  # opcional
    }
    """
    try:
        # Normalizar campos básicos
        nombre = str(ingrediente_data.get('name') or ingrediente_data.get('id', '')).strip()
        if not nombre:
            return {'ingrediente': None, 'accion': 'omitido', 'error': 'Nombre vacío'}

        categoria = ingrediente_data.get('category') or ingrediente_data.get('categoria', 'otros')
        unidad = ingrediente_data.get('unit') or ingrediente_data.get('unidad', 'unidades')

        # Cantidad
        try:
            cantidad = float(ingrediente_data.get('quantity') or ingrediente_data.get('cantidad', 0))
        except (TypeError, ValueError):
            return {'ingrediente': nombre, 'accion': 'omitido', 'error': 'Cantidad inválida'}

        # Confianza
        confianza = ingrediente_data.get('confidence', ingrediente_data.get('confianza', 1.0))
        try:
            confianza = float(confianza)
        except (TypeError, ValueError):
            confianza = 1.0
        confianza = max(0.0, min(1.0, confianza))

        emoji = ingrediente_data.get('emoji', None)

        # Bounding box normalization (si viene)
        bounding_box = ingrediente_data.get('bounding_box', None)
        if isinstance(bounding_box, dict):
            try:
                bbox = {
                    'x': float(bounding_box.get('x', 0.5)),
                    'y': float(bounding_box.get('y', 0.5)),
                    'width': float(bounding_box.get('width', 0.1)),
                    'height': float(bounding_box.get('height', 0.1))
                }
                bbox = {k: max(0.0, min(1.0, v)) for k, v in bbox.items()}
                bounding_box = bbox
            except Exception:
                bounding_box = None
        else:
            bounding_box = None

        # Búsqueda case-insensitive por nombre
        nombre_norm = nombre.lower()
        ingrediente = Ingrediente.query.filter(
            db.func.lower(Ingrediente.nombre) == nombre_norm
        ).first()

        # Crear ingrediente si no existe (con manejo de race condition)
        if not ingrediente:
            try:
                ingrediente = Ingrediente(
                    nombre=nombre.title(),
                    categoria=categoria,
                    unidad=unidad,
                    emoji=emoji
                )
                db.session.add(ingrediente)
                db.session.flush()  # para obtener id
            except IntegrityError:
                db.session.rollback()
                ingrediente = Ingrediente.query.filter(
                    db.func.lower(Ingrediente.nombre) == nombre_norm
                ).first()
                if not ingrediente:
                    try:
                        ingrediente = Ingrediente(
                            nombre=nombre.title(),
                            categoria=categoria,
                            unidad=unidad,
                            emoji=emoji
                        )
                        db.session.add(ingrediente)
                        db.session.flush()
                    except Exception as ex:
                        db.session.rollback()
                        return {'ingrediente': nombre, 'accion': 'error', 'error': str(ex)}

        # Actualizar emoji si viene y no está en DB
        if emoji and not ingrediente.emoji:
            ingrediente.emoji = emoji

        # Buscar inventario del usuario para el ingrediente
        inventario_item = Inventario.query.filter_by(
            usuario_id=usuario_id,
            ingrediente_id=ingrediente.id
        ).first()

        if inventario_item:
            inventario_item.cantidad = cantidad
            inventario_item.confianza = confianza
            if bounding_box:
                inventario_item.bounding_box = bounding_box
            accion = 'actualizado'
        else:
            inventario_item = Inventario(
                usuario_id=usuario_id,
                ingrediente_id=ingrediente.id,
                cantidad=cantidad,
                confianza=confianza,
                bounding_box=bounding_box
            )
            db.session.add(inventario_item)
            accion = 'agregado'

        return {
            'ingrediente': ingrediente.nombre,
            'accion': accion,
            'cantidad': cantidad,
            'confianza': confianza,
            'ingrediente_id': ingrediente.id,
            'emoji': ingrediente.emoji,
            'bounding_box': inventario_item.bounding_box if inventario_item else None
        }

    except Exception as e:
        db.session.rollback()
        return {'ingrediente': None, 'accion': 'error', 'error': str(e)}


@inventory_bp.route('/v1/ingredientes', methods=['GET'])
def obtener_inventario():
    """
    Obtener inventario de usuario
    ---
    tags:
      - Inventario
    parameters:
      - name: userId
        in: query
        type: integer
        required: true
        description: ID del usuario
    responses:
      200:
        description: Inventario del usuario
        schema:
          type: object
          properties:
            usuario_id:
              type: integer
              example: 1
            inventario:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  ingrediente:
                    type: object
                    properties:
                      id:
                        type: integer
                        example: 1
                      nombre:
                        type: string
                        example: "Tomate"
                      categoria:
                        type: string
                        example: "verdura"
                      unidad:
                        type: string
                        example: "unidades"
                      emoji:
                        type: string
                        example: "🍅"
                  cantidad:
                    type: number
                    example: 3.0
                  confianza:
                    type: number
                    example: 0.95
                  bounding_box:
                    type: object
                    properties:
                      x:
                        type: number
                        example: 0.25
                      y:
                        type: number
                        example: 0.3
                      width:
                        type: number
                        example: 0.2
                      height:
                        type: number
                        example: 0.25
                  fecha_actualizacion:
                    type: string
                    format: date-time
                    example: "2024-01-15T10:30:00"
            total_ingredientes:
              type: integer
              example: 5
      400:
        description: Parámetro userId requerido
      404:
        description: Usuario no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        user_id_raw = request.args.get('userId')
        if not user_id_raw:
            return jsonify({'error': 'Se requiere el parámetro userId'}), 400

        try:
            user_id = int(user_id_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'userId inválido'}), 400

        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        inventario_items = Inventario.query.filter_by(usuario_id=user_id).all()

        inventario = []
        for item in inventario_items:
            inventario.append({
                'id': item.id,
                'ingrediente': {
                    'id': item.ingrediente.id if item.ingrediente else None,
                    'nombre': item.ingrediente.nombre if item.ingrediente else None,
                    'categoria': item.ingrediente.categoria if item.ingrediente else None,
                    'unidad': item.ingrediente.unidad if item.ingrediente else None,
                    'emoji': item.ingrediente.emoji if item.ingrediente else None
                },
                'cantidad': float(item.cantidad) if item.cantidad is not None else 0.0,
                'confianza': float(item.confianza) if item.confianza is not None else 1.0,
                'bounding_box': item.bounding_box,
                'fecha_actualizacion': item.fecha_actualizacion.isoformat() if item.fecha_actualizacion else None
            })

        return jsonify({
            'usuario_id': user_id,
            'inventario': inventario,
            'total_ingredientes': len(inventario)
        }), 200

    except Exception as e:
        print(f"Error obteniendo inventario: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
