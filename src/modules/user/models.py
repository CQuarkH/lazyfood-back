from core.database import db
from datetime import datetime, timedelta
import json


class Usuario(db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    pais = db.Column(db.String(50))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    nivel_cocina = db.Column(db.Integer, default=1)  # 1: principiante, 2: intermedio, 3: avanzado
    activo = db.Column(db.Boolean, default=True)

    # Relaciones
    preferencias = db.relationship('Preferencia', backref='usuario', uselist=False, cascade='all, delete-orphan')
    inventario = db.relationship('Inventario', backref='usuario', cascade='all, delete-orphan')
    sugerencias = db.relationship('SugerenciaReceta', backref='usuario', cascade='all, delete-orphan')
    planificador = db.relationship('Planificador', backref='usuario', cascade='all, delete-orphan')
    tokens = db.relationship('Token', backref='usuario', cascade='all, delete-orphan')

    def to_dict(self):
        """Convertir usuario a diccionario"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'correo': self.correo,
            'pais': self.pais,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'nivel_cocina': self.nivel_cocina,
            'activo': self.activo
        }


class Preferencia(db.Model):
    __tablename__ = 'preferencia'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False, unique=True)
    dieta = db.Column(db.String(50))  # 'vegano', 'vegetariano', 'keto', etc.
    alergias = db.Column(db.JSON)  # Lista de alergias como JSON
    gustos = db.Column(db.JSON)  # Lista de gustos como JSON

    def to_dict(self):
        """Convertir preferencias a diccionario"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'dieta': self.dieta,
            'alergias': self.alergias or [],
            'gustos': self.gustos or []
        }


class Token(db.Model):
    __tablename__ = 'token'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    jwt = db.Column(db.Text, nullable=False)
    fecha_expiracion = db.Column(db.DateTime, nullable=False)

    def is_expired(self):
        """Verificar si el token ha expirado"""
        return datetime.utcnow() > self.fecha_expiracion