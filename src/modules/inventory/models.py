from core.database import db
from datetime import datetime


class Ingrediente(db.Model):
    __tablename__ = 'ingrediente'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))
    unidad = db.Column(db.String(20))

    # Relaciones
    inventarios = db.relationship('Inventario', backref='ingrediente', cascade='all, delete-orphan')

    def to_dict(self):
        """Convertir ingrediente a diccionario"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'categoria': self.categoria,
            'unidad': self.unidad
        }


class Inventario(db.Model):
    __tablename__ = 'inventario'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ingrediente_id = db.Column(db.Integer, db.ForeignKey('ingrediente.id'), nullable=False)
    cantidad = db.Column(db.Numeric(10, 2))
    confianza = db.Column(db.Numeric(3, 2), default=1.0)  # Nivel de confianza de la detección
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Restricción única para evitar duplicados
    __table_args__ = (db.UniqueConstraint('usuario_id', 'ingrediente_id', name='uq_usuario_ingrediente'),)

    def to_dict(self):
        """Convertir inventario a diccionario"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'ingrediente_id': self.ingrediente_id,
            'ingrediente_nombre': self.ingrediente.nombre if self.ingrediente else None,
            'cantidad': float(self.cantidad) if self.cantidad else 0,
            'confianza': float(self.confianza) if self.confianza else 1.0,
            'categoria': self.ingrediente.categoria if self.ingrediente else None,
            'unidad': self.ingrediente.unidad if self.ingrediente else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }