from core.database import db
from modules.user.models import Usuario
from modules.inventory.models import Inventario
from modules.recipe.models import Receta, SugerenciaReceta
from modules.planner.models import Planificador
from modules.ai.gemini_service import gemini_service
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger("lazyfood.planning")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


class PlanningService:
    """
    Servicio para obtener y generar planificaciones semanales.

    - obtener_planificacion(usuario_id, fecha_inicio): devuelve la planificación guardada (si existe).
    - generar_sugerencias_planificacion(usuario_id, fecha_inicio): genera planificación via Gemini,
      normaliza los valores a IDs enteros válidos, persiste Planificador(es) con es_sugerida=True
      y devuelve el JSON resultante.
    """

    def __init__(self):
        self.gemini_service = gemini_service

    # -------------------------
    # Obtener planificación desde DB
    # -------------------------
    def obtener_planificacion(self, usuario_id: int, fecha_inicio: str) -> Dict[str, Any]:
        """
        Obtener la planificación semanal de un usuario desde DB.

        Retorna:
            { 'semana': 'YYYY-MM-DD', 'menus': { 'YYYY-MM-DD': { 'desayuno': {receta_id..., es_sugerida...}, ... } } }
        Nota: Planificador.get_semana_usuario ya devuelve para cada comida un dict con receta_id y es_sugerida.
        """
        try:
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                raise ValueError("Usuario no encontrado")

            planificacion = Planificador.get_semana_usuario(usuario_id, fecha_inicio)
            return {
                'semana': fecha_inicio,
                'menus': planificacion
            }
        except Exception as e:
            logger.exception("Error obteniendo planificación: %s", e)
            return {
                'semana': fecha_inicio,
                'menus': {}
            }

    # -------------------------
    # Generar planificación por IA (y persistir)
    # -------------------------
    def generar_sugerencias_planificacion(self, usuario_id: int, fecha_inicio: str) -> Dict[str, Any]:
        """
        Generar sugerencias de planificación semanal usando Gemini AI, normalizar a IDs de recetas
        que el usuario ya tiene (SugerenciaReceta -> Receta) y persistir en la tabla Planificador.

        Devuelve:
          { 'semana': 'YYYY-MM-DD', 'sugerencias': { 'YYYY-MM-DD': { 'desayuno': int|null, 'almuerzo': int|null, 'cena': int|null } } }
        """
        try:
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                return {'error': 'Usuario no encontrado', 'codigo': 'usuario_no_encontrado'}

            # Obtener sugerencias previas (recetas que el usuario "tiene")
            sugerencias_db = SugerenciaReceta.query.filter_by(usuario_id=usuario_id) \
                .order_by(SugerenciaReceta.fecha.desc()) \
                .limit(200) \
                .all()

            if not sugerencias_db:
                logger.info("Usuario %s no tiene sugerencias previas", usuario_id)
                return {'error': 'No hay recetas sugeridas para el usuario. Genera recomendaciones antes de solicitar planificación por IA.', 'codigo': 'no_recetas_usuario'}

            recetas_user = []
            recetas_by_id = {}
            recetas_by_name_norm = {}
            for s in sugerencias_db:
                if not s.receta:
                    continue
                r = s.receta
                recetas_user.append({'id': r.id, 'nombre': r.nombre})
                recetas_by_id[r.id] = r
                nombre_norm = (r.nombre or "").strip().lower()
                if nombre_norm:
                    recetas_by_name_norm[nombre_norm] = r.id

            if not recetas_user:
                logger.info("Usuario %s tiene sugerencias, pero sin recetas válidas", usuario_id)
                return {'error': 'No hay recetas válidas asociadas a tus sugerencias.', 'codigo': 'no_recetas_validas'}

            # Preparar inventario y preferencias para el prompt (opcional)
            inventario_items = Inventario.query.filter_by(usuario_id=usuario_id).all()
            ingredientes = [item.ingrediente.nombre for item in inventario_items if getattr(item, "ingrediente", None)]
            preferencias = {}
            if getattr(usuario, "preferencias", None):
                try:
                    preferencias = usuario.preferencias.to_dict()
                except Exception:
                    preferencias = {
                        'dieta': getattr(usuario.preferencias, 'dieta', None),
                        'alergias': getattr(usuario.preferencias, 'alergias', []) or [],
                        'gustos': getattr(usuario.preferencias, 'gustos', []) or []
                    }

            recetas_para_gemini = [{'id': r['id'], 'nombre': r['nombre']} for r in recetas_user]

            # Llamada a Gemini (puede devolver strings con placeholders como "ID_RECETA_1")
            try:
                raw_plan = self.gemini_service.generar_planificacion_semanal(
                    ingredientes=ingredientes,
                    preferencias=preferencias,
                    nivel_cocina=usuario.nivel_cocina,
                    recetas_sugeridas=recetas_para_gemini,
                    fecha_inicio=fecha_inicio
                )
            except Exception as e:
                logger.exception("Error llamando a Gemini: %s", e)
                # fallback a planificación por defecto con IDs de usuario (cíclica)
                return self._planificacion_por_defecto_con_ids(fecha_inicio, recetas_user)

            # Normalizar raw_plan
            plan_sugerencias = None
            semana_en_raw = None
            if isinstance(raw_plan, dict):
                plan_sugerencias = raw_plan.get('sugerencias') or raw_plan.get('menus') or raw_plan.get('planificacion')
                semana_en_raw = raw_plan.get('semana') or raw_plan.get('week') or semana_en_raw
            else:
                plan_sugerencias = None

            if not plan_sugerencias:
                logger.warning("Gemini no devolvió clave 'sugerencias'/'menus' -> fallback")
                return self._planificacion_por_defecto_con_ids(fecha_inicio, recetas_user)

            # Post-procesar (resolver a ids enteros)
            cleaned = {}
            for fecha_str, comidas in plan_sugerencias.items():
                # normalizar fecha a YYYY-MM-DD si es posible
                try:
                    datetime.strptime(fecha_str, '%Y-%m-%d')
                except Exception:
                    m = re.search(r'\d{4}-\d{2}-\d{2}', str(fecha_str))
                    if m:
                        fecha_str = m.group(0)
                    else:
                        logger.debug("Ignorando fecha no normalizable: %s", fecha_str)
                        continue

                cleaned[fecha_str] = {}
                if not isinstance(comidas, dict):
                    cleaned[fecha_str] = {'desayuno': None, 'almuerzo': None, 'cena': None}
                    continue

                for tipo in ['desayuno', 'almuerzo', 'cena']:
                    raw_val = comidas.get(tipo)
                    resolved = self._resolver_receta_id(raw_val, recetas_by_id, recetas_by_name_norm)
                    cleaned[fecha_str][tipo] = resolved

            # Persistir en DB: limpiar semana y guardar las entradas con es_sugerida=True
            try:
                # limpiar semana existente
                Planificador.limpiar_semana_usuario(usuario_id, fecha_inicio)

                # Guardar cada entrada (solo donde haya receta_id != None)
                for fecha_str, comidas in cleaned.items():
                    try:
                        fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    except Exception:
                        logger.debug("Fecha inválida al persistir, omitiendo: %s", fecha_str)
                        continue

                    for tipo_comida, receta_id in comidas.items():
                        if receta_id is None:
                            # no crear registro si no hay receta asignada
                            continue

                        # verificar existencia de receta
                        receta_obj = Receta.query.get(int(receta_id))
                        if not receta_obj:
                            logger.debug("Receta id %s no existe en DB al persistir, omitiendo", receta_id)
                            continue

                        plan = Planificador(
                            usuario_id=usuario_id,
                            fecha=fecha_dt,
                            tipo_comida=tipo_comida,
                            receta_id=int(receta_id),
                            es_sugerida=True
                        )
                        db.session.add(plan)

                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.exception("Error persistiendo planificación generada: %s", e)
                # Aunque la persistencia falle, devolvemos la planificación generada (pero con aviso)
                return {
                    'semana': semana_en_raw or fecha_inicio,
                    'sugerencias': cleaned,
                    'warning': 'No se pudo guardar la planificación en la base de datos'
                }

            return {
                'semana': semana_en_raw or fecha_inicio,
                'sugerencias': cleaned
            }

        except Exception as e:
            logger.exception("Error en generar_sugerencias_planificacion: %s", e)
            # fallback
            return self._planificacion_por_defecto_con_ids(fecha_inicio, [])

    # -------------------------
    # Helpers
    # -------------------------
    def _resolver_receta_id(self, raw_value: Any, recetas_by_id: Dict[int, Receta], recetas_by_name_norm: Dict[str, int]) -> Optional[int]:
        """
        Resolver raw_value (int, 'ID_RECETA_1', nombre, dict, etc) a un ID entero válido.
        """
        try:
            if raw_value is None:
                return None

            # int directo
            if isinstance(raw_value, int):
                if Receta.query.get(raw_value):
                    return int(raw_value)
                return None

            if isinstance(raw_value, dict):
                # { "id": 12 } o {"receta_id": 12}
                for key in ('id', 'receta_id', 'recipe_id'):
                    v = raw_value.get(key)
                    if v:
                        try:
                            v_int = int(v)
                            if Receta.query.get(v_int):
                                return v_int
                        except Exception:
                            pass
                # intentar por 'nombre'
                nombre = raw_value.get('nombre') or raw_value.get('name')
                if nombre:
                    s_norm = str(nombre).strip().lower()
                    if s_norm in recetas_by_name_norm:
                        return recetas_by_name_norm[s_norm]
                    # contains
                    for name_norm, rid in recetas_by_name_norm.items():
                        if name_norm in s_norm or s_norm in name_norm:
                            return rid
                return None

            # string -> extraer dígitos
            if isinstance(raw_value, str):
                s = raw_value.strip()
                # sólo dígitos
                m_full = re.fullmatch(r'\d+', s)
                if m_full:
                    cid = int(s)
                    if Receta.query.get(cid):
                        return cid
                # primer número en string
                m = re.search(r'(\d+)', s)
                if m:
                    cid = int(m.group(1))
                    if Receta.query.get(cid):
                        return cid
                # si es formato "ID_RECETA_1" -> extraer número
                m2 = re.search(r'receta[_\-]?\s*id[_\-]?\s*(\d+)', s, re.IGNORECASE)
                if m2:
                    cid = int(m2.group(1))
                    if Receta.query.get(cid):
                        return cid
                # intentar resolver por nombre (case-insensitive)
                s_norm = s.lower()
                if s_norm in recetas_by_name_norm:
                    return recetas_by_name_norm[s_norm]
                for name_norm, rid in recetas_by_name_norm.items():
                    if name_norm in s_norm or s_norm in name_norm:
                        return rid

            return None
        except Exception as e:
            logger.exception("Error resolviendo receta id para valor %r: %s", raw_value, e)
            return None

    def _planificacion_por_defecto_con_ids(self, fecha_inicio: str, recetas_user: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Devuelve una planificación por defecto asignando cíclicamente IDs de recetas_user.
        """
        try:
            fecha_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except Exception:
            fecha_dt = datetime.utcnow()
            fecha_inicio = fecha_dt.strftime('%Y-%m-%d')

        sugerencias = {}
        receta_ids = [r['id'] for r in recetas_user] if recetas_user else []
        for i in range(7):
            d = (fecha_dt + timedelta(days=i)).strftime('%Y-%m-%d')
            if receta_ids:
                sugerencias[d] = {
                    'desayuno': receta_ids[(i * 3) % len(receta_ids)],
                    'almuerzo': receta_ids[(i * 3 + 1) % len(receta_ids)],
                    'cena': receta_ids[(i * 3 + 2) % len(receta_ids)]
                }
            else:
                sugerencias[d] = {'desayuno': None, 'almuerzo': None, 'cena': None}
        return {'semana': fecha_inicio, 'sugerencias': sugerencias}


# Instancia global
planning_service = PlanningService()
