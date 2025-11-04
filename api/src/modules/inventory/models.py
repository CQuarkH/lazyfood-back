# modules/inventory/models.py
from core.database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB


class Ingrediente(db.Model):
    __tablename__ = 'ingrediente'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))
    unidad = db.Column(db.String(20))
    emoji = db.Column(db.String(8))  # emoji representativo

    # Relaciones
    inventarios = db.relationship('Inventario', backref='ingrediente', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'categoria': self.categoria,
            'unidad': self.unidad,
            'emoji': self.emoji
        }


class Inventario(db.Model):
    __tablename__ = 'inventario'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ingrediente_id = db.Column(db.Integer, db.ForeignKey('ingrediente.id'), nullable=False)
    cantidad = db.Column(db.Numeric(10, 2))
    confianza = db.Column(db.Numeric(3, 2), default=1.0)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bounding_box = db.Column(JSONB)  # {x,y,width,height}

    __table_args__ = (db.UniqueConstraint('usuario_id', 'ingrediente_id', name='uq_usuario_ingrediente'),)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'ingrediente_id': self.ingrediente_id,
            'ingrediente_nombre': self.ingrediente.nombre if self.ingrediente else None,
            'cantidad': float(self.cantidad) if self.cantidad is not None else 0.0,
            'confianza': float(self.confianza) if self.confianza is not None else 1.0,
            'categoria': self.ingrediente.categoria if self.ingrediente else None,
            'unidad': self.ingrediente.unidad if self.ingrediente else None,
            'emoji': self.ingrediente.emoji if self.ingrediente else None,
            'bounding_box': self.bounding_box,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }
