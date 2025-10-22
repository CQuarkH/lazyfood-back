from core.database import db
from datetime import datetime, timedelta


class Planificador(db.Model):
    __tablename__ = 'planificador'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo_comida = db.Column(db.String(20), nullable=False)  # 'desayuno', 'almuerzo', 'cena'
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.id'))
    es_sugerida = db.Column(db.Boolean, default=False)

    # Restricción única para evitar duplicados en el mismo día y comida
    __table_args__ = (db.UniqueConstraint('usuario_id', 'fecha', 'tipo_comida', name='uq_usuario_fecha_comida'),)

    def to_dict(self):
        """Convertir planificador a diccionario"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'tipo_comida': self.tipo_comida,
            'receta_id': self.receta_id,
            'receta_nombre': self.receta.nombre if self.receta else None,
            'receta_tiempo': self.receta.tiempo_preparacion if self.receta else None,
            'receta_calorias': self.receta.calorias if self.receta else None,
            'receta_nivel': self.receta.nivel_dificultad if self.receta else None,
            'es_sugerida': self.es_sugerida
        }

    @classmethod
    def get_semana_usuario(cls, usuario_id, fecha_inicio):
        """Obtener planificación semanal para un usuario"""
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = fecha_inicio_dt + timedelta(days=6)

            planes = cls.query.filter(
                cls.usuario_id == usuario_id,
                cls.fecha >= fecha_inicio_dt,
                cls.fecha <= fecha_fin
            ).all()

            # Organizar por fecha y tipo de comida
            resultado = {}
            for plan in planes:
                fecha_str = plan.fecha.isoformat()
                if fecha_str not in resultado:
                    resultado[fecha_str] = {}

                resultado[fecha_str][plan.tipo_comida] = {
                    'receta_id': plan.receta_id,
                    'receta_nombre': plan.receta.nombre if plan.receta else None,
                    'es_sugerida': plan.es_sugerida
                }

            return resultado
        except Exception as e:
            print(f"Error obteniendo planificación semanal: {e}")
            return {}

    @classmethod
    def limpiar_semana_usuario(cls, usuario_id, fecha_inicio):
        """Eliminar todas las entradas de planificación de una semana"""
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = fecha_inicio_dt + timedelta(days=6)

            # Eliminar entradas existentes para esa semana
            cls.query.filter(
                cls.usuario_id == usuario_id,
                cls.fecha >= fecha_inicio_dt,
                cls.fecha <= fecha_fin
            ).delete()

            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error limpiando planificación semanal: {e}")
            return False