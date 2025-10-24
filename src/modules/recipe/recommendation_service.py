from core.database import db
from modules.user.models import Usuario, Preferencia
from modules.inventory.models import Inventario
from modules.recipe.models import Receta, SugerenciaReceta
from modules.ai.gemini_service import gemini_service
from typing import List, Dict, Any
from datetime import datetime


class RecommendationService:
    """Servicio para generar y gestionar recomendaciones de recetas"""

    def __init__(self):
        self.gemini_service = gemini_service

    def generar_recomendaciones(self, usuario_id: int) -> List[Dict[str, Any]]:
        """
        Generar recomendaciones de recetas para un usuario

        Args:
            usuario_id: ID del usuario

        Returns:
            Lista de recetas recomendadas
        """
        try:
            # Obtener datos del usuario
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                raise ValueError("Usuario no encontrado")

            # Obtener inventario del usuario
            inventario_items = Inventario.query.filter_by(usuario_id=usuario_id).all()
            ingredientes = [item.ingrediente.nombre for item in inventario_items]

            # Obtener preferencias
            preferencias = {}
            if usuario.preferencias:
                preferencias = {
                    'dieta': usuario.preferencias.dieta,
                    'alergias': usuario.preferencias.alergias or [],
                    'gustos': usuario.preferencias.gustos or []
                }

            # Generar recetas con Gemini
            recetas_generadas = self.gemini_service.generar_recetas(
                ingredientes, preferencias, usuario.nivel_cocina
            )

            # Calcular porcentajes de coincidencia y guardar en base de datos
            recetas_con_coincidencia = []
            for receta_data in recetas_generadas:
                porcentaje = self._calcular_coincidencia(ingredientes, receta_data)

                # Guardar en base de datos
                receta_db = self._guardar_receta_sugerida(usuario_id, receta_data, porcentaje)

                # Formatear respuesta
                receta_data['id'] = receta_db.id
                receta_data['porcentaje_coincidencia'] = porcentaje
                recetas_con_coincidencia.append(receta_data)

            return recetas_con_coincidencia

        except Exception as e:
            print(f"Error generando recomendaciones: {str(e)}")
            raise

    def _calcular_coincidencia(self, ingredientes_usuario: List[str], receta: Dict[str, Any]) -> float:
        """
        Calcular porcentaje de coincidencia entre ingredientes del usuario y receta

        Args:
            ingredientes_usuario: Lista de ingredientes del usuario
            receta: Datos de la receta generada

        Returns:
            Porcentaje de coincidencia (0-100)
        """
        if not receta.get('ingredientes'):
            return 0.0

        # Normalizar nombres de ingredientes
        ingredientes_usuario_norm = [ing.lower().strip() for ing in ingredientes_usuario]
        ingredientes_receta_norm = [
            ing['nombre'].lower().strip() for ing in receta['ingredientes']
        ]

        # Contar coincidencias
        coincidencias = 0
        for ing_receta in ingredientes_receta_norm:
            # Buscar coincidencia parcial (por si hay nombres similares)
            if any(ing_receta in ing_user or ing_user in ing_receta
                   for ing_user in ingredientes_usuario_norm):
                coincidencias += 1

        if not ingredientes_receta_norm:
            return 0.0

        porcentaje = (coincidencias / len(ingredientes_receta_norm)) * 100
        return round(porcentaje, 2)

    def _guardar_receta_sugerida(self, usuario_id: int, receta_data: Dict[str, Any],
                                 porcentaje_coincidencia: float) -> SugerenciaReceta:
        """
        Guardar la receta sugerida en la base de datos

        Args:
            usuario_id: ID del usuario
            receta_data: Datos de la receta
            porcentaje_coincidencia: Porcentaje calculado

        Returns:
            Instancia de SugerenciaReceta guardada
        """
        # Buscar si ya existe una receta con el mismo nombre
        receta_existente = Receta.query.filter_by(nombre=receta_data['nombre']).first()

        if not receta_existente:
            # Crear nueva receta
            receta_existente = Receta(
                nombre=receta_data['nombre'],
                tiempo_preparacion=receta_data['tiempo'],
                calorias=receta_data['calorias'],
                nivel_dificultad=receta_data['nivel'],
                imagen_url=f"https://cdn.lazyfood.com/recetas/{receta_data['nombre'].lower().replace(' ', '_')}.jpg"
            )
            db.session.add(receta_existente)
            db.session.flush()  # Para obtener el ID

        # Crear registro de sugerencia
        sugerencia = SugerenciaReceta(
            usuario_id=usuario_id,
            receta_id=receta_existente.id,
            porcentaje_coincidencia=porcentaje_coincidencia
        )
        db.session.add(sugerencia)
        db.session.commit()

        return sugerencia

    def obtener_historial_recomendaciones(self, usuario_id: int, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Obtener historial de recomendaciones previas

        Args:
            usuario_id: ID del usuario
            limite: Número máximo de recomendaciones a devolver

        Returns:
            Lista de recomendaciones previas
        """
        sugerencias = SugerenciaReceta.query.filter_by(usuario_id=usuario_id) \
            .order_by(SugerenciaReceta.fecha.desc()) \
            .limit(limite) \
            .all()

        resultado = []
        for sugerencia in sugerencias:
            receta_data = {
                'id': sugerencia.receta.id,
                'nombre': sugerencia.receta.nombre,
                'tiempo': sugerencia.receta.tiempo_preparacion,
                'calorias': sugerencia.receta.calorias,
                'nivel': sugerencia.receta.nivel_dificultad,
                'porcentaje_coincidencia': float(sugerencia.porcentaje_coincidencia),
                'fecha': sugerencia.fecha.isoformat()
            }
            resultado.append(receta_data)

        return resultado


# Instancia global del servicio
recommendation_service = RecommendationService()