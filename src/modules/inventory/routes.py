from flask import Blueprint, request, jsonify
from core.database import db
from core.auth_middleware import token_required
from core.role_middleware import owner_or_admin_required
from modules.user.models import Usuario
from modules.inventory.models import Ingrediente, Inventario

# Crear Blueprint para inventario
inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/v1/ingredientes', methods=['PUT'])
@token_required
def actualizar_inventario():
    """
    Actualizar inventario de usuario
    ---
    tags:
      - Inventario
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Token JWT en formato "Bearer {token}"
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
              description: Lista de ingredientes detectados
              items:
                type: object
                properties:
                  nombre:
                    type: string
                    example: "Tomate"
                    description: Nombre del ingrediente
                  categoria:
                    type: string
                    example: "verdura"
                    description: Categoría del ingrediente
                  confianza:
                    type: number
                    format: float
                    example: 0.95
                    description: Nivel de confianza de la detección (0-1)
                  cantidad:
                    type: number
                    format: float
                    example: 3
                    description: Cantidad del ingrediente
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
        # Obtener parámetros
        user_id = request.args.get('userId')

        if not user_id:
            return jsonify({'error': 'Se requiere el parámetro userId'}), 400

        # Verificar que el usuario existe
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Obtener y validar datos del cuerpo
        data = request.get_json()
        if not data or 'ingredientes' not in data:
            return jsonify({'error': 'Datos inválidos, se esperaba una lista de ingredientes'}), 400

        ingredientes_data = data['ingredientes']

        # Validar estructura de cada ingrediente
        for ingrediente_data in ingredientes_data:
            if not all(key in ingrediente_data for key in ['nombre', 'cantidad']):
                return jsonify({'error': 'Cada ingrediente debe tener nombre y cantidad'}), 400

        # Procesar cada ingrediente
        resultados = []
        for ingrediente_data in ingredientes_data:
            resultado = _procesar_ingrediente(usuario.id, ingrediente_data)
            resultados.append(resultado)

        # Confirmar cambios en la base de datos
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
    Procesa un ingrediente individual: lo busca o crea, y actualiza el inventario
    """
    nombre = ingrediente_data['nombre'].strip().title()
    categoria = ingrediente_data.get('categoria', 'otros')
    cantidad = float(ingrediente_data['cantidad'])
    confianza = ingrediente_data.get('confianza', 1.0)

    # Buscar ingrediente por nombre (case insensitive)
    ingrediente = Ingrediente.query.filter(
        db.func.lower(Ingrediente.nombre) == db.func.lower(nombre)
    ).first()

    # Si no existe, crear nuevo ingrediente
    if not ingrediente:
        ingrediente = Ingrediente(
            nombre=nombre,
            categoria=categoria,
            unidad='unidades'  # Unidad por defecto
        )
        db.session.add(ingrediente)
        db.session.flush()  # Para obtener el ID sin hacer commit

    # Buscar si ya existe en el inventario del usuario
    inventario_item = Inventario.query.filter_by(
        usuario_id=usuario_id,
        ingrediente_id=ingrediente.id
    ).first()

    # Actualizar o crear registro de inventario
    if inventario_item:
        inventario_item.cantidad = cantidad
        inventario_item.confianza = confianza
        accion = 'actualizado'
    else:
        inventario_item = Inventario(
            usuario_id=usuario_id,
            ingrediente_id=ingrediente.id,
            cantidad=cantidad,
            confianza=confianza
        )
        db.session.add(inventario_item)
        accion = 'agregado'

    return {
        'ingrediente': nombre,
        'accion': accion,
        'cantidad': cantidad,
        'confianza': confianza
    }


@inventory_bp.route('/v1/ingredientes', methods=['GET'])
@token_required
def obtener_inventario():
    """
    Obtener inventario de usuario
    ---
    tags:
      - Inventario
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Token JWT en formato "Bearer {token}"
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
                  cantidad:
                    type: number
                    example: 3.0
                  confianza:
                    type: number
                    example: 0.95
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
        user_id = request.args.get('userId')

        if not user_id:
            return jsonify({'error': 'Se requiere el parámetro userId'}), 400

        # Verificar que el usuario existe
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Obtener inventario del usuario
        inventario_items = Inventario.query.filter_by(usuario_id=user_id).all()

        inventario = []
        for item in inventario_items:
            inventario.append({
                'id': item.id,
                'ingrediente': {
                    'id': item.ingrediente.id,
                    'nombre': item.ingrediente.nombre,
                    'categoria': item.ingrediente.categoria,
                    'unidad': item.ingrediente.unidad
                },
                'cantidad': float(item.cantidad) if item.cantidad else 0,
                'confianza': float(item.confianza) if item.confianza else 1.0,
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