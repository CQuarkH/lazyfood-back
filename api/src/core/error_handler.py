"""
Manejador global de errores para la aplicación Flask
Captura excepciones no manejadas y proporciona respuestas consistentes
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException
import traceback


def register_error_handlers(app):
    """
    Registra los manejadores de error globales en la aplicación Flask
    
    Args:
        app: Instancia de la aplicación Flask
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        """Manejador para errores 400 Bad Request"""
        return jsonify({
            'error': 'Datos inválidos'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Manejador para errores 401 Unauthorized"""
        return jsonify({
            'error': 'No autorizado'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Manejador para errores 403 Forbidden"""
        return jsonify({
            'error': 'Acceso denegado'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Manejador para errores 404 Not Found"""
        return jsonify({
            'error': 'Recurso no encontrado'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Manejador para errores 405 Method Not Allowed"""
        return jsonify({
            'error': 'Método no permitido'
        }), 405
    
    @app.errorhandler(409)
    def conflict(error):
        """Manejador para errores 409 Conflict"""
        return jsonify({
            'error': 'Conflicto con el estado actual'
        }), 409
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Manejador para errores 422 Unprocessable Entity"""
        return jsonify({
            'error': 'Entidad no procesable'
        }), 422
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Manejador para errores 500 Internal Server Error"""
        # Log del error para debugging
        app.logger.error(f'Error interno del servidor: {str(error)}')
        if app.debug:
            app.logger.error(traceback.format_exc())
        
        return jsonify({
            'error': 'Ocurrió un error interno. Intente más tarde.'
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Manejador genérico para todas las excepciones HTTP de Werkzeug"""
        response = {
            'error': error.description or 'Error en la solicitud'
        }
        return jsonify(response), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Manejador para excepciones no capturadas"""
        # Log del error completo
        app.logger.error(f'Error inesperado: {str(error)}')
        app.logger.error(traceback.format_exc())
        
        # En producción, no revelar detalles del error
        if app.debug or app.config.get('TESTING'):
            return jsonify({
                'error': 'Error inesperado',
                'detalle': str(error),
                'tipo': error.__class__.__name__
            }), 500
        
        return jsonify({
            'error': 'Ocurrió un error interno. Intente más tarde.'
        }), 500


class APIException(Exception):
    """
    Excepción personalizada para la API
    Permite lanzar errores con código de estado HTTP específico
    """
    
    def __init__(self, message: str, status_code: int = 400, payload: dict = None):
        """
        Inicializa la excepción
        
        Args:
            message: Mensaje de error
            status_code: Código HTTP del error
            payload: Datos adicionales del error
        """
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        """Convierte la excepción a diccionario"""
        error_dict = {'error': self.message}
        if self.payload:
            error_dict.update(self.payload)
        return error_dict


def register_api_exception_handler(app):
    """
    Registra el manejador para APIException
    
    Args:
        app: Instancia de la aplicación Flask
    """
    
    @app.errorhandler(APIException)
    def handle_api_exception(error):
        """Manejador para APIException"""
        return jsonify(error.to_dict()), error.status_code
