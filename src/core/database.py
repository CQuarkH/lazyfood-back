from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base para todos los modelos"""
    pass


# Inicializar SQLAlchemy
db = SQLAlchemy(model_class=Base)


def init_db(app):
    """Inicializar la base de datos con la aplicación Flask"""
    db.init_app(app)

    with app.app_context():
        # Importar todos los modelos aquí para que SQLAlchemy los detecte
        from modules.user.models import Usuario, Preferencia, Token
        from modules.inventory.models import Ingrediente, Inventario
        from modules.recipe.models import Receta, PasoReceta, SugerenciaReceta
        from modules.planner.models import Planificador

        # Crear todas las tablas
        db.create_all()
        print("✓ Base de datos inicializada y tablas creadas")

        # Verificar conexión
        try:
            db.session.execute(db.text('SELECT 1'))
            print("✓ Conexión a la base de datos establecida")
        except Exception as e:
            print(f"✗ Error conectando a la base de datos: {e}")
            raise


def get_db_session():
    """Obtener sesión de base de datos para operaciones fuera del contexto de Flask"""
    return db.session