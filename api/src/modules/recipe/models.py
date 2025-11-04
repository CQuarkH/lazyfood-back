# modules/recipe/models.py
from core.database import db


class Receta(db.Model):
    __tablename__ = 'receta'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    tiempo_preparacion = db.Column(db.Integer)  # en minutos
    calorias = db.Column(db.Integer)  # calorías por porción
    nivel_dificultad = db.Column(db.Integer, default=1)  # 1: fácil, 2: medio, 3: difícil
    emoji = db.Column(db.String(8))  # emoji representativo

    # Relaciones
    pasos = db.relationship('PasoReceta', backref='receta', cascade='all, delete-orphan',
                            order_by='PasoReceta.numero_paso')
    sugerencias = db.relationship('SugerenciaReceta', backref='receta', cascade='all, delete-orphan')
    planificaciones = db.relationship('Planificador', backref='receta', cascade='all, delete-orphan')

    def to_dict(self, include_pasos=False):
        data = {
            'id': self.id,
            'nombre': self.nombre,
            'tiempo': self.tiempo_preparacion,
            'calorias': self.calorias,
            'nivel': self.nivel_dificultad,
            'emoji': self.emoji
        }

        if include_pasos:
            data['pasos'] = [paso.to_dict() for paso in self.pasos]

        return data


class PasoReceta(db.Model):
    __tablename__ = 'paso_receta'

    id = db.Column(db.Integer, primary_key=True)
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.id'), nullable=False)
    numero_paso = db.Column(db.Integer, nullable=False)
    instruccion = db.Column(db.Text, nullable=False)
    temporizador_segundos = db.Column(db.Integer)  # segundos para el temporizador

    __table_args__ = (db.UniqueConstraint('receta_id', 'numero_paso', name='uq_receta_paso'),)

    def to_dict(self):
        return {
            'n': self.numero_paso,
            'instruccion': self.instruccion,
            'timer': self.temporizador_segundos
        }


class SugerenciaReceta(db.Model):
    __tablename__ = 'sugerencia_receta'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.id'), nullable=False)
    porcentaje_coincidencia = db.Column(db.Numeric(5, 2))  # 0.00 a 100.00
    fecha = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'receta_id': self.receta_id,
            'receta_nombre': self.receta.nombre if self.receta else None,
            'porcentaje_coincidencia': float(self.porcentaje_coincidencia) if self.porcentaje_coincidencia else 0,
            'fecha': self.fecha.isoformat() if self.fecha else None
        }
