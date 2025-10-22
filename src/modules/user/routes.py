from flask import Blueprint, jsonify
from core.database import db
from modules.user.models import Usuario

# Crear Blueprint para usuarios
user_bp = Blueprint('user', __name__)


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
            # Agregar información de preferencias si existe
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