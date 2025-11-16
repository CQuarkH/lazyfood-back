from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
import os
import sys

from core.config import Config
from core.database import init_db
from core.error_handler import register_error_handlers, register_api_exception_handler

# Importar blueprints
from modules.inventory.routes import inventory_bp
from modules.user.routes import user_bp
from modules.recipe.routes import recipe_bp
from modules.planner.routes import planner_bp
from modules.auth.routes import auth_bp
from modules.test_routes import test_bp


def create_app():
    """Factory function para crear la aplicación Flask"""
    app = Flask(__name__)

    # Configuración
    app.config.from_object(Config)

    # Configuración de Swagger
    app.config['SWAGGER'] = {
        'title': 'LazyFood API',
        'uiversion': 3,
        'specs_route': '/docs/',
        'specs': [
            {
                'endpoint': 'apispec',
                'route': '/apispec.json',
                'rule_filter': lambda rule: True,
                'model_filter': lambda tag: True,
            }
        ],
        'static_url_path': '/flasgger_static',
        'swagger_ui': True,
        'description': 'API para el sistema de recomendación de recetas LazyFood',
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'Token JWT en formato: Bearer {token}'
            }
        }
    }

    # Inicializar Swagger
    swagger = Swagger(app)

    # Validar configuración
    try:
        Config.validate_config()
    except ValueError as e:
        print(f"Error de configuración: {e}")
        return None

    # Inicializar extensiones
    try:
        init_db(app)
        
        # Configuración de CORS mejorada
        CORS(app, 
             resources={r"/*": {
                 "origins": Config.CORS_ORIGINS,
                 "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "expose_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "max_age": 3600
             }})
        
        print("✓ CORS configurado")
        
    except Exception as e:
        print(f"Error inicializando la aplicación: {e}")
        return None

    # Registrar manejadores de error globales
    register_error_handlers(app)
    register_api_exception_handler(app)
    print("✓ Manejadores de error registrados")
    
    # Registrar blueprints
    app.register_blueprint(auth_bp)  # Blueprint de autenticación primero
    app.register_blueprint(inventory_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(recipe_bp)
    app.register_blueprint(planner_bp)
    
    # Configuración de Rate Limiting (después de registrar blueprints)
    if Config.RATELIMIT_ENABLED:
        try:
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                storage_uri=Config.RATELIMIT_STORAGE_URL,
                default_limits=[Config.RATELIMIT_DEFAULT],
                headers_enabled=Config.RATELIMIT_HEADERS_ENABLED
            )
            
            # Aplicar rate limit específico al endpoint de login
            limiter.limit("5 per minute")(auth_bp)
            
            print("✓ Rate limiting habilitado")
        except Exception as e:
            print(f"⚠️  Warning: Rate limiting no pudo inicializarse: {e}")
            print("   La aplicación funcionará sin rate limiting")

    # Ruta de salud (sin autenticación)
    @app.route('/health')
    def health():
        """
        Health Check del sistema
        ---
        tags:
          - Sistema
        responses:
          200:
            description: Estado del sistema
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: healthy
                database:
                  type: string
                  example: connected
        """
        from core.database import db
        try:
            # Verificar conexión a la base de datos
            db.session.execute(db.text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'

        return jsonify({
            'status': 'healthy',
            'database': db_status
        })

    # Ruta principal
    @app.route('/')
    def home():
        """
        Página principal de la API
        ---
        tags:
          - Sistema
        responses:
          200:
            description: Información de la API
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: LazyFood API está funcionando!
                version:
                  type: string
                  example: 1.0.0
                status:
                  type: string
                  example: active
                docs:
                  type: string
                  example: /docs
        """
        return jsonify({
            'message': 'LazyFood API está funcionando!',
            'version': '1.0.0',
            'status': 'active',
            'docs': '/docs'
        })

    # Manejo de errores global
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint no encontrado'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Error interno del servidor'}), 500

    print("✓ Aplicación Flask inicializada correctamente")
    print("✓ Swagger configurado en /docs")
    print("✓ Blueprint de autenticación registrado")
    print("✓ Blueprint de inventario registrado")
    print("✓ Blueprint de usuarios registrado")
    print("✓ Blueprint de recetas registrado")
    print("✓ Blueprint de planificador registrado")
    return app


if __name__ == '__main__':
    app = create_app()
    if app:
        app.run(
            host='0.0.0.0',
            port=Config.PORT,
            debug=Config.DEBUG
        )
    else:
        print("✗ No se pudo inicializar la aplicación")
        sys.exit(1)