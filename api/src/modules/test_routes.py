"""
Endpoint de prueba para el manejador de respuestas
Ruta: /test/responses
"""
from flask import Blueprint, request
from core.response_handler import response, errors, success
from core.error_handler import APIException

test_bp = Blueprint('test', __name__)


@test_bp.route('/test/responses', methods=['GET'])
def test_responses():
    """
    Endpoint de prueba para diferentes tipos de respuestas
    ---
    tags:
      - Testing
    parameters:
      - in: query
        name: type
        type: string
        required: true
        description: Tipo de respuesta a probar (success, error, not_found, etc.)
        enum:
          - success
          - created
          - bad_request
          - unauthorized
          - forbidden
          - not_found
          - conflict
          - internal_error
          - exception
    responses:
      200:
        description: Respuesta de prueba exitosa
      400:
        description: Bad request de prueba
      401:
        description: Unauthorized de prueba
      403:
        description: Forbidden de prueba
      404:
        description: Not found de prueba
      409:
        description: Conflict de prueba
      500:
        description: Internal error de prueba
    """
    response_type = request.args.get('type', 'success')
    
    if response_type == 'success':
        return response.success(
            data={'message': 'Esta es una respuesta exitosa de prueba'},
            message='Operación exitosa'
        )
    
    elif response_type == 'created':
        return response.created(
            data={'id': 123, 'name': 'Test Resource'},
            message=success.USER_CREATED
        )
    
    elif response_type == 'bad_request':
        return response.bad_request(errors.INVALID_DATA)
    
    elif response_type == 'unauthorized':
        return response.unauthorized(errors.TOKEN_MISSING)
    
    elif response_type == 'forbidden':
        return response.forbidden(errors.FORBIDDEN)
    
    elif response_type == 'not_found':
        return response.not_found(errors.USER_NOT_FOUND)
    
    elif response_type == 'conflict':
        return response.conflict(errors.USER_ALREADY_EXISTS)
    
    elif response_type == 'internal_error':
        return response.internal_error()
    
    elif response_type == 'exception':
        # Esto lanzará una excepción que será capturada por el manejador global
        raise APIException(
            message="Esta es una excepción personalizada de prueba",
            status_code=422,
            payload={'detail': 'Información adicional del error'}
        )
    
    else:
        return response.bad_request('Tipo de respuesta no válido')
