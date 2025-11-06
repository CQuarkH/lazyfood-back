import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuración base de la aplicación"""

    # Configuración general
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', '5000'))

    # Configuración JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'dev-jwt-secret-key'))
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))  # 1 hora
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '2592000'))  # 30 días

    # Configuración de base de datos
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://lazyfood_user:lazyfood_pass@localhost:5432/lazyfood_db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True
    }

    # Configuración de Google AI (Gemini)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    # Configuración de correo electrónico
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', 'noreply@lazyfood.com'))

    # Configuración de CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # Configuración de Rate Limiting
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_HEADERS_ENABLED = True

    @classmethod
    def validate_config(cls):
        """Validar que todas las configuraciones requeridas estén presentes"""
        required_vars = ['DATABASE_URL', 'SECRET_KEY']
        missing_vars = []

        for var in required_vars:
            value = getattr(cls, var, None)
            if not value:
                missing_vars.append(var)

        # Verificar API key de Gemini (solo warning si no está)
        if not cls.GEMINI_API_KEY:
            print("⚠️  ADVERTENCIA: GEMINI_API_KEY no configurada. Las recomendaciones no funcionarán.")

        if missing_vars:
            raise ValueError(f"Faltan variables de entorno requeridas: {', '.join(missing_vars)}")

        print("✓ Configuración validada correctamente")
        print(f"✓ Database URL: {cls.DATABASE_URL}")
        print(f"✓ Secret Key configurada: {'Sí' if cls.SECRET_KEY else 'No'}")
        print(f"✓ JWT Secret Key configurada: {'Sí' if cls.JWT_SECRET_KEY else 'No'}")
        print(f"✓ Gemini API Key: {'Configurada' if cls.GEMINI_API_KEY else 'NO CONFIGURADA'}")
        print(f"✓ Rate Limiting: {'Habilitado' if cls.RATELIMIT_ENABLED else 'Deshabilitado'}")