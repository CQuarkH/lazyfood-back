from core.database import db
from modules.user.models import Usuario
from modules.inventory.models import Inventario
from modules.recipe.models import Receta, SugerenciaReceta
from modules.planner.models import Planificador
from modules.ai.gemini_service import gemini_service
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json
import re


class PlanningService:
    """Servicio para generar y gestionar planificación semanal"""

    def __init__(self):
        self.gemini_service = gemini_service

    def generar_sugerencias_planificacion(self, usuario_id: int, fecha_inicio: str) -> Dict[str, Any]:
        """
        Generar sugerencias de planificación semanal usando Gemini AI

        Args:
            usuario_id: ID del usuario
            fecha_inicio: Fecha de inicio de la semana (YYYY-MM-DD)

        Returns:
            Diccionario con la planificación sugerida
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

            # Obtener recetas sugeridas recientemente
            recetas_sugeridas = self._obtener_recetas_sugeridas(usuario_id)

            # Generar planificación con Gemini
            planificacion = self.gemini_service.generar_planificacion_semanal(
                ingredientes, preferencias, usuario.nivel_cocina, recetas_sugeridas, fecha_inicio
            )

            return planificacion

        except Exception as e:
            print(f"Error generando sugerencias de planificación: {str(e)}")
            # En caso de error, devolver planificación por defecto
            return self._planificacion_por_defecto(fecha_inicio)

    def _obtener_recetas_sugeridas(self, usuario_id: int) -> List[Dict[str, Any]]:
        """Obtener recetas sugeridas recientemente para el usuario"""
        try:
            sugerencias = SugerenciaReceta.query.filter_by(usuario_id=usuario_id) \
                .order_by(SugerenciaReceta.fecha.desc()) \
                .limit(20) \
                .all()

            recetas = []
            for sug in sugerencias:
                recetas.append({
                    'id': sug.receta.id,
                    'nombre': sug.receta.nombre,
                    'tiempo': sug.receta.tiempo_preparacion,
                    'calorias': sug.receta.calorias,
                    'nivel': sug.receta.nivel_dificultad,
                    'porcentaje_coincidencia': float(sug.porcentaje_coincidencia) if sug.porcentaje_coincidencia else 0
                })

            return recetas
        except Exception as e:
            print(f"Error obteniendo recetas sugeridas: {e}")
            return []

    def guardar_planificacion(self, usuario_id: int, planificacion_data: Dict[str, Any]) -> bool:
        """
        Guardar la planificación semanal en la base de datos

        Args:
            usuario_id: ID del usuario
            planificacion_data: Datos de la planificación

        Returns:
            True si se guardó correctamente
        """
        try:
            semana = planificacion_data.get('semana')
            menus = planificacion_data.get('menus', {})

            if not semana:
                raise ValueError("Se requiere la fecha de inicio de la semana")

            # Limpiar planificación existente para esa semana
            Planificador.limpiar_semana_usuario(usuario_id, semana)

            # Guardar nueva planificación
            for fecha_str, comidas in menus.items():
                try:
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

                    for tipo_comida, receta_id in comidas.items():
                        if receta_id:  # Solo si hay una receta asignada
                            # Verificar que la receta existe
                            receta = Receta.query.get(receta_id)
                            if not receta:
                                print(f"Advertencia: Receta {receta_id} no encontrada, omitiendo...")
                                continue

                            plan = Planificador(
                                usuario_id=usuario_id,
                                fecha=fecha,
                                tipo_comida=tipo_comida,
                                receta_id=receta_id,
                                es_sugerida=False  # Porque el usuario la está guardando explícitamente
                            )
                            db.session.add(plan)
                except ValueError as e:
                    print(f"Error procesando fecha {fecha_str}: {e}")
                    continue

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error guardando planificación: {str(e)}")
            raise

    def obtener_planificacion(self, usuario_id: int, fecha_inicio: str) -> Dict[str, Any]:
        """
        Obtener la planificación semanal de un usuario

        Args:
            usuario_id: ID del usuario
            fecha_inicio: Fecha de inicio de la semana (YYYY-MM-DD)

        Returns:
            Diccionario con la planificación
        """
        try:
            planificacion = Planificador.get_semana_usuario(usuario_id, fecha_inicio)

            return {
                'semana': fecha_inicio,
                'menus': planificacion
            }
        except Exception as e:
            print(f"Error obteniendo planificación: {e}")
            return {
                'semana': fecha_inicio,
                'menus': {}
            }

    def _planificacion_por_defecto(self, fecha_inicio: str) -> Dict[str, Any]:
        """Planificación por defecto en caso de error de Gemini"""
        try:
            fecha = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            sugerencias = {}

            # Obtener algunas recetas básicas de la base de datos
            recetas_basicas = Receta.query.limit(5).all()

            for i in range(7):
                fecha_str = (fecha + timedelta(days=i)).strftime('%Y-%m-%d')
                sugerencias[fecha_str] = {
                    "desayuno": recetas_basicas[0].id if len(recetas_basicas) > 0 else None,
                    "almuerzo": recetas_basicas[1].id if len(recetas_basicas) > 1 else None,
                    "cena": recetas_basicas[2].id if len(recetas_basicas) > 2 else None
                }

            return {
                "semana": fecha_inicio,
                "sugerencias": sugerencias
            }
        except Exception as e:
            print(f"Error creando planificación por defecto: {e}")
            return {
                "semana": fecha_inicio,
                "sugerencias": {}
            }


# Instancia global del servicio
planning_service = PlanningService()