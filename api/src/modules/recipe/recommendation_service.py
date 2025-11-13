from core.database import db
from modules.user.models import Usuario
from modules.inventory.models import Inventario
from modules.recipe.models import Receta, SugerenciaReceta, PasoReceta
from modules.ai.gemini_service import gemini_service
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("lazyfood.recommendation")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


class RecommendationService:
    """Servicio para generar y gestionar recomendaciones de recetas"""

    def __init__(self):
        self.gemini = gemini_service

    # -------------------------
    # Recomendaciones (metadatos rápidos)
    # -------------------------
    def generar_recomendaciones(self, usuario_id: int, cantidad: int = 5) -> List[Dict[str, Any]]:
        """
        Genera recomendaciones rápidas (metadatos) usando Gemini (rápido).
        No genera pasos (para optimizar latencia); los pasos se generan bajo demanda
        usando generar_y_guardar_pasos.

        Args:
            usuario_id: ID del usuario para obtener inventario y preferencias.
            cantidad: número máximo de recetas solicitadas al modelo (por defecto 5).
                      Se normaliza a un entero en el rango [1, 20].

        Returns:
            Lista de diccionarios con metadata de recetas.
        """
        # Normalizar / validar 'cantidad'
        try:
            if cantidad is None:
                cantidad = 5
            else:
                cantidad = int(cantidad)
        except Exception:
            cantidad = 5

        # Forzar límites razonables
        if cantidad < 1:
            cantidad = 1
        if cantidad > 20:
            cantidad = 20

        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            raise ValueError("Usuario no encontrado")

        inventario_items = Inventario.query.filter_by(usuario_id=usuario_id).all()
        ingredientes = [item.ingrediente.nombre for item in inventario_items if getattr(item, "ingrediente", None)]

        preferencias = {}
        if getattr(usuario, "preferencias", None):
            # asumir que usuario.preferencias tiene atributos o método to_dict
            try:
                preferencias = usuario.preferencias.to_dict()
            except Exception:
                preferencias = {
                    'dieta': getattr(usuario.preferencias, 'dieta', None),
                    'alergias': getattr(usuario.preferencias, 'alergias', []) or [],
                    'gustos': getattr(usuario.preferencias, 'gustos', []) or []
                }

        # Llamada optimizada: pedir solo metadata (nombre, tiempo, calorias, nivel, emoji, lista de ingredientes)
        try:
            recetas_generadas = self.gemini.generar_recetas_metadata(ingredientes, preferencias, usuario.nivel_cocina, cantidad=cantidad)
        except Exception as e:
            logger.exception("Error llamando a Gemini para metadata: %s", e)
            recetas_generadas = []

        if not recetas_generadas:
            recetas_generadas = self.gemini._recetas_por_defecto()

        recetas_con_coincidencia = []
        for receta_data in recetas_generadas:
            porcentaje = self._calcular_coincidencia(ingredientes, receta_data)
            receta_db = self._guardar_receta_minima(receta_data)

            # crear sugerencia en DB
            try:
                sugerencia = SugerenciaReceta(usuario_id=usuario_id, receta_id=receta_db.id, porcentaje_coincidencia=porcentaje)
                db.session.add(sugerencia)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.exception("Error guardando sugerencia: %s", e)

            receta_salida = {
                'id': receta_db.id,
                'nombre': receta_data.get('nombre'),
                'tiempo': receta_data.get('tiempo'),
                'calorias': receta_data.get('calorias'),
                'nivel': receta_data.get('nivel', 1),
                'emoji': receta_data.get('emoji'),
                'razon': receta_data.get('razon', f"Coincide {porcentaje}% con tus ingredientes"),
                'ingredientes': receta_data.get('ingredientes', []),
                'porcentaje_coincidencia': porcentaje
            }

            recetas_con_coincidencia.append(receta_salida)

        return recetas_con_coincidencia

    # -------------------------
    # Nuevo método: generar y guardar pasos para una receta
    # -------------------------
    def generar_y_guardar_pasos(self,
                                receta_id: int,
                                usuario_id: Optional[int] = None,
                                ingredientes_override: Optional[List[Dict[str, Any]]] = None,
                                nivel_cocina_override: Optional[int] = None,
                                max_steps: Optional[int] = 20) -> List[Dict[str, Any]]:
        """
        Genera pasos detallados para una receta (usando Gemini) y los persiste en DB.
        Flujo de ingredientes (prioridad):
          1. Ingredientes asociados a la receta en DB (modelo IngredienteReceta si existe).
          2. Inventario del usuario (si se pasa usuario_id).
          3. ingredientes_override (parámetro explícito, último recurso).
        Devuelve la lista de pasos guardados [{n,instruccion,timer},...]
        """
        # Validar receta
        receta = Receta.query.get(receta_id)
        if not receta:
            raise ValueError("Receta no encontrada")

        # Determinar preferencias y nivel de cocina
        preferencias = {}
        nivel_cocina = nivel_cocina_override or getattr(receta, "nivel_dificultad", None) or 1
        if usuario_id:
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                raise ValueError("Usuario no encontrado")
            nivel_cocina = nivel_cocina_override or getattr(usuario, "nivel_cocina", 1) or 1
            if getattr(usuario, "preferencias", None):
                try:
                    preferencias = usuario.preferencias.to_dict()
                except Exception:
                    preferencias = {
                        'dieta': getattr(usuario.preferencias, 'dieta', None),
                        'alergias': getattr(usuario.preferencias, 'alergias', []) or [],
                        'gustos': getattr(usuario.preferencias, 'gustos', []) or []
                    }

        # 1) Intentar leer ingredientes específicos de la receta (si el modelo existe)
        ingredientes_para_prompt: List[Dict[str, Any]] = []
        try:
            # Intentamos importar un posible modelo IngredienteReceta en modules.recipe.models
            from modules.recipe.models import IngredienteReceta  # si no existe, excepción se captura
            items = IngredienteReceta.query.filter_by(receta_id=receta_id).all()
            for it in items:
                nombre = getattr(it, "nombre", None) or getattr(it, "name", None)
                cantidad = getattr(it, "cantidad", None) or getattr(it, "quantity", None)
                unidad = getattr(it, "unidad", None) or getattr(it, "unit", None)
                emoji = getattr(it, "emoji", None)
                if nombre:
                    ingredientes_para_prompt.append({
                        'nombre': nombre,
                        'cantidad': cantidad,
                        'unidad': unidad,
                        'emoji': emoji
                    })
        except Exception:
            # modelo no existe o error leyendo -> seguimos adelante
            logger.debug("No hay modelo IngredienteReceta o error al leerlo; se usará inventario/override si aplica")

        # 2) Si no hay ingredientes en receta, intentar usar inventario del usuario
        if not ingredientes_para_prompt and usuario_id:
            try:
                inventario_items = Inventario.query.filter_by(usuario_id=usuario_id).all()
                for it in inventario_items:
                    ing = getattr(it, "ingrediente", None)
                    if not ing:
                        continue
                    nombre = getattr(ing, "nombre", None) or getattr(ing, "name", None)
                    cantidad = getattr(it, "cantidad", None) or 0
                    unidad = getattr(it, "unidad", None) or getattr(ing, "unidad", None) or ""
                    emoji = getattr(ing, "emoji", None)
                    if nombre:
                        ingredientes_para_prompt.append({
                            'nombre': nombre,
                            'cantidad': cantidad,
                            'unidad': unidad,
                            'emoji': emoji
                        })
            except Exception as e:
                logger.exception("Error leyendo inventario para usuario_id=%s: %s", usuario_id, e)

        # 3) Si aún vacío, usar ingredientes_override si se pasó
        if not ingredientes_para_prompt and ingredientes_override:
            for ing in ingredientes_override:
                nombre = ing.get('nombre') or ing.get('name')
                if not nombre:
                    continue
                ingredientes_para_prompt.append({
                    'nombre': nombre,
                    'cantidad': ing.get('cantidad'),
                    'unidad': ing.get('unidad'),
                    'emoji': ing.get('emoji')
                })

        # Llamada a Gemini para generar pasos detallados
        try:
            pasos_generados = self.gemini.generar_pasos_detallados(
                receta.nombre,
                ingredientes=ingredientes_para_prompt,
                preferencias=preferencias,
                nivel_cocina=nivel_cocina,
                max_steps=max_steps
            )
        except Exception as e:
            logger.exception("Error llamando a Gemini para generar pasos: %s", e)
            pasos_generados = []

        if not pasos_generados:
            logger.warning("Gemini no devolvió pasos para receta_id=%s", receta_id)
            return []

        # Helper local para conversión segura a int
        def _safe_int(value):
            if value is None:
                return None
            try:
                return int(value)
            except Exception:
                try:
                    # intentar parsear strings numéricos con espacios
                    return int(str(value).strip())
                except Exception:
                    return None

        # Persistir pasos (reemplazando los existentes para idempotencia)
        try:
            existentes = PasoReceta.query.filter_by(receta_id=receta_id).all()
            if existentes:
                for e in existentes:
                    db.session.delete(e)
                db.session.flush()

            # Asegurar numeración consecutiva si alguno viene sin 'n'
            contador = 1
            for p in pasos_generados:
                n = p.get('n') or p.get('numero') or None
                instruccion = p.get('instruccion') or p.get('instruction') or p.get('texto') or ""
                timer = p.get('timer', None)

                if n is None:
                    n = contador
                    contador += 1

                # Convertir timer a entero seguro; el campo en la BD se llama temporizador_segundos
                temporizador = _safe_int(timer)
                if timer is not None and temporizador is None:
                    logger.debug("Valor de timer inválido para receta_id=%s paso_n=%s: %r", receta_id, n, timer)

                paso_obj = PasoReceta(
                    receta_id=receta_id,
                    numero_paso=int(n),
                    instruccion=instruccion,
                    temporizador_segundos=temporizador
                )
                db.session.add(paso_obj)

            db.session.commit()

            # Leer pasos guardados y devolverlos
            guardados = PasoReceta.query.filter_by(receta_id=receta_id).order_by(PasoReceta.numero_paso).all()
            salida = [p.to_dict() for p in guardados]
            return salida

        except Exception as e:
            db.session.rollback()
            logger.exception("Error guardando pasos en DB para receta_id=%s: %s", receta_id, e)
            return []

    # -------------------------
    # Helpers privados
    # -------------------------
    def _calcular_coincidencia(self, ingredientes_usuario: List[str], receta: Dict[str, Any]) -> float:
        if not receta.get('ingredientes'):
            return 0.0

        ingredientes_usuario_norm = [ing.lower().strip() for ing in ingredientes_usuario]
        ingredientes_receta_norm = [ing.get('nombre','').lower().strip() for ing in receta['ingredientes']]

        coincidencias = 0
        for ing_rec in ingredientes_receta_norm:
            if any(ing_rec in ing_user or ing_user in ing_rec for ing_user in ingredientes_usuario_norm):
                coincidencias += 1

        if not ingredientes_receta_norm:
            return 0.0

        porcentaje = (coincidencias / len(ingredientes_receta_norm)) * 100
        return round(porcentaje, 2)

    def _guardar_receta_minima(self, receta_data: Dict[str, Any]) -> Receta:
        receta_existente = Receta.query.filter_by(nombre=receta_data['nombre']).first()
        if not receta_existente:
            receta_existente = Receta(
                nombre=receta_data.get('nombre'),
                tiempo_preparacion=receta_data.get('tiempo'),
                calorias=receta_data.get('calorias'),
                nivel_dificultad=receta_data.get('nivel', 1),
                emoji=receta_data.get('emoji')
            )
            db.session.add(receta_existente)
            db.session.flush()
        return receta_existente

    def obtener_historial_recomendaciones(self, usuario_id: int, limite: int = 10) -> List[Dict[str, Any]]:
        sugerencias = SugerenciaReceta.query.filter_by(usuario_id=usuario_id) \
            .order_by(SugerenciaReceta.fecha.desc()) \
            .limit(limite) \
            .all()
        resultado = []
        for s in sugerencias:
            resultado.append({
                'id': s.receta.id,
                'nombre': s.receta.nombre,
                'tiempo': s.receta.tiempo_preparacion,
                'calorias': s.receta.calorias,
                'nivel': s.receta.nivel_dificultad,
                'porcentaje_coincidencia': float(s.porcentaje_coincidencia) if s.porcentaje_coincidencia else 0,
                'fecha': s.fecha.isoformat() if s.fecha else None
            })
        return resultado


# Instancia global
recommendation_service = RecommendationService()
