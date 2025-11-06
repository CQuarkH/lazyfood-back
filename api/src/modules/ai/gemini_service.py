# api/src/modules/ai/gemini_service.py
from datetime import datetime
from google import genai
from google.genai import types
import json
import re
import logging
from core.config import Config
from typing import List, Dict, Any, Optional

# Logger sencillo que saldrá en stdout (docker logs)
logger = logging.getLogger("lazyfood.gemini")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class GeminiService:
    def __init__(self):
        # BLOQUE OBLIGATORIO: no modificar ni eliminar
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = Config.GEMINI_MODEL
        self.client = None
        self.model = None
        self.model_config = None
        self._initialize()

    def _initialize(self):
        """Inicializar el cliente de Gemini"""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY no está configurada")

        self.client = genai.Client(api_key=self.api_key)
        self.model = self.client.models
        # Mantener temperature=0 tal y como pediste
        self.model_config = types.GenerateContentConfig(temperature=0)
        logger.info("✓ Gemini AI inicializado con modelo: %s", self.model_name)

    # -------------------------
    # Método A: metadata de recetas (rápido, sin pasos)
    # -------------------------
    def generar_recetas_metadata(self,
                                 ingredientes: List[str],
                                 preferencias: Dict[str, Any],
                                 nivel_cocina: int,
                                 cantidad: int = 5) -> List[Dict[str, Any]]:
        """
        Genera metadata de recetas (rápida): nombre, tiempo, calorias, nivel, razon, emoji,
        ingredientes (nombre,cantidad,unidad,emoji,en_inventario).
        Reintenta una vez con más tokens si detecta truncamiento/incompleto.
        """
        try:
            prompt = self._prompt_metadata(ingredientes, preferencias, nivel_cocina, cantidad)
            # intento controlado para latencia (temperature 0)
            config = types.GenerateContentConfig(temperature=0)
            response = self.model.generate_content(model=self.model_name, contents=prompt, config=config)

            # debug: volcar representación
            try:
                logger.debug("Gemini raw response repr: %s", repr(response))
            except Exception:
                logger.debug("Gemini raw response (str): %s", str(response))

            texto = self._extract_text_from_sdk_response(response)
            logger.debug("Gemini extracted text (trunc 2000): %s", texto[:2000].replace("\n", "\\n"))

            recetas = self._parsear_array_recetas_es(texto)
            if recetas:
                return recetas

            # comprobar truncamiento e intentar reintento
            truncated = self._is_truncated_response(response, texto)
            if truncated:
                logger.info("Respuesta truncada detectada. Reintentando con más tokens...")
                try:
                    config2 = types.GenerateContentConfig(temperature=0, max_output_tokens=3000)
                    response2 = self.model.generate_content(model=self.model_name, contents=prompt, config=config2)
                    try:
                        logger.debug("Gemini raw response repr (retry): %s", repr(response2))
                    except Exception:
                        logger.debug("Gemini raw response (retry str): %s", str(response2))

                    texto2 = self._extract_text_from_sdk_response(response2)
                    logger.debug("Gemini extracted text retry (trunc 2000): %s", texto2[:2000].replace("\n", "\\n"))

                    recetas = self._parsear_array_recetas_es(texto2)
                    if recetas:
                        return recetas

                    recetas = self._parsear_fallback_plaintext(texto2)
                    if recetas:
                        return recetas
                except Exception as e:
                    logger.exception("Reintento falló: %s", e)

            # fallback tolerante sobre primer texto
            logger.warning("No se pudo parsear respuesta estructurada; intentando parser tolerante del primer texto")
            recetas = self._parsear_fallback_plaintext(texto)
            if recetas:
                return recetas

            logger.info("No se generaron recetas válidas; devolviendo recetas por defecto")
            return self._recetas_por_defecto()

        except Exception as e:
            logger.exception("Error generar_recetas_metadata: %s", e)
            return self._recetas_por_defecto()

    def _prompt_metadata(self, ingredientes: List[str], preferencias: Dict[str, Any], nivel_cocina: int, cantidad: int) -> str:
        nivel_texto = {1: "principiante", 2: "intermedio", 3: "avanzado"}.get(nivel_cocina, "principiante")
        ingredientes_txt = ", ".join(ingredientes) if ingredientes else "ninguno"
        dieta = preferencias.get("dieta", "omnivoro")
        alergias = ", ".join(preferencias.get("alergias", [])) if preferencias.get("alergias") else "ninguna"
        gustos = ", ".join(preferencias.get("gustos", [])) if preferencias.get("gustos") else "ninguno"

        prompt = f"""
Eres un chef experto y nutricionista. Genera como MAXIMO {cantidad} recetas en ESPAÑOL.
Devuelve SÓLO un ARRAY JSON válido y compacto (sin texto adicional) — PARA CADA RECETA: metadata y lista breve de ingredientes.
La dieta, alergias, gustos o nivel de cocina son campos opcionales, pero los ingredientes son obligatorios.

CONTEXTO:
- Ingredientes disponibles: {ingredientes_txt}
- Dieta: {dieta}
- Alergias: {alergias}
- Gustos: {gustos}
- Nivel de cocina: {nivel_texto}

FORMATO EXACTO (claves en ESPAÑOL — usa exactamente estas claves):
[
  {{
    "nombre": "Nombre de la receta",
    "tiempo": 15,
    "calorias": 250,
    "nivel": 1,
    "razon": "Coincide X% con tus ingredientes y es apta para [dieta]",
    "emoji": "🍽️",
    "ingredientes": [
      {{
        "nombre": "tomate",
        "cantidad": 2,
        "unidad": "unidades",
        "emoji": "🍅",
        "en_inventario": true
      }}
    ]
  }}
]

Reglas:
- Prioriza ingredientes disponibles.
- Respeta alergias y dieta.
- Mantén la respuesta compacta y estrictamente JSON.
"""
        return prompt

    # -------------------------
    # Método B: pasos detallados por receta (separado, on-demand)
    # -------------------------
    def generar_pasos_detallados(self,
                                 nombre_receta: str,
                                 ingredientes: Optional[List[Dict[str, Any]]] = None,
                                 preferencias: Optional[Dict[str, Any]] = None,
                                 nivel_cocina: int = 1,
                                 max_steps: Optional[int] = 20) -> List[Dict[str, Any]]:
        """
        Genera pasos detallados para UNA receta. Responde con lista de objetos:
        [{ "n": 1, "instruccion": "...", "timer": 60 }, ...]
        Este método puede tardar más que metadata; por eso está separado.
        """
        try:
            prompt = self._prompt_pasos(nombre_receta, ingredientes or [], preferencias or {}, nivel_cocina, max_steps)
            config = types.GenerateContentConfig(temperature=0)
            response = self.model.generate_content(model=self.model_name, contents=prompt, config=config)

            try:
                logger.debug("Gemini raw response repr (pasos): %s", repr(response))
            except Exception:
                logger.debug("Gemini raw response (pasos str): %s", str(response))

            texto = self._extract_text_from_sdk_response(response)
            logger.debug("Gemini pasos extracted text (trunc 2000): %s", texto[:2000].replace("\n", "\\n"))

            pasos = self._parsear_pasos(texto)
            if pasos:
                return pasos

            logger.warning("No se parsearon pasos; intentando parseo tolerante")
            pasos = self._parsear_pasos_fallback_from_plaintext(texto)
            return pasos
        except Exception as e:
            logger.exception("Error generar_pasos_detallados: %s", e)
            return []

    def generar_pasos_receta(self, *args, **kwargs):
        return self.generar_pasos_detallados(*args, **kwargs)

    def _prompt_pasos(self, nombre_receta: str, ingredientes: List[Dict[str, Any]], preferencias: Dict[str, Any], nivel_cocina: int, max_steps: Optional[int]) -> str:
        nivel_texto = {1: "principiante", 2: "intermedio", 3: "avanzado"}.get(nivel_cocina, "principiante")
        ingredientes_txt = ", ".join([ing.get("nombre") or ing.get("name") or "" for ing in ingredientes]) if ingredientes else "ninguno"
        dieta = preferencias.get("dieta", "omnivoro")
        alergias = ", ".join(preferencias.get("alergias", [])) if preferencias.get("alergias") else "ninguna"
        max_steps_txt = f"(máx {max_steps} pasos)" if max_steps else ""

        prompt = f"""
Eres un chef profesional. Genera PASOS para preparar la receta: "{nombre_receta}" {max_steps_txt}.
La dieta, alergias, gustos o nivel de cocina son campos opcionales, pero los ingredientes son obligatorios.
Contexto:
- Ingredientes: {ingredientes_txt}
- Dieta: {dieta}
- Alergias: {alergias}
- Nivel de cocina: {nivel_texto}

Devuelve SÓLO un ARRAY JSON con objetos EXACTOS con estas claves:
[
  {{
    "n": 1,
    "instruccion": "Instrucción clara y secuencial",
    "timer": 120
  }}
]

Reglas:
- Numerar pasos consecutivos a partir de 1.
- Timer en segundos si aplica (ej: 300), o null si no aplica.
- Máximo {max_steps if max_steps else 'no especificado'} pasos.
- No incluyas texto explicativo adicional, sólo el JSON.
"""
        return prompt

    # -------------------------
    # Método C: planificación semanal (mantener funcionalidad)
    # -------------------------
    def generar_planificacion_semanal(self, ingredientes: List[str], preferencias: Dict[str, Any],
                                      nivel_cocina: int, recetas_sugeridas: List[Dict[str, Any]],
                                      fecha_inicio: str) -> Dict[str, Any]:
        """
        Generar planificación semanal de menús usando Gemini AI.
        Mantiene el comportamiento original: devuelve un dict con 'semana' y 'sugerencias' {}
        """
        try:
            prompt = self._construir_prompt_planificacion(ingredientes, preferencias, nivel_cocina, recetas_sugeridas, fecha_inicio)
            # respetar configuración por defecto (temperature=0)
            config = types.GenerateContentConfig(temperature=0)
            response = self.model.generate_content(model=self.model_name, contents=prompt, config=config)
            texto = self._extract_text_from_sdk_response(response)
            logger.debug("Gemini planificacion extracted text (trunc 2000): %s", texto[:2000].replace("\n", "\\n"))
            planificacion = self._parsear_respuesta_planificacion(texto)
            return planificacion
        except Exception as e:
            logger.exception("Error generando planificación con Gemini: %s", e)
            return self._planificacion_por_defecto(fecha_inicio)

    def _construir_prompt_planificacion(self, ingredientes: List[str], preferencias: Dict[str, Any],
                                        nivel_cocina: int, recetas_sugeridas: List[Dict[str, Any]],
                                        fecha_inicio: str) -> str:
        nivel_texto = {1: "principiante", 2: "intermedio", 3: "avanzado"}.get(nivel_cocina, "principiante")
        recetas_texto = ""
        for receta in (recetas_sugeridas or [])[:10]:
            recetas_texto += f"- {receta.get('nombre')} (ID: {receta.get('id')}, Tiempo: {receta.get('tiempo')}min, Calorías: {receta.get('calorias')}, Nivel: {receta.get('nivel')})\n"

        prompt = f"""
Eres un nutricionista y chef experto. Genera una planificación semanal de menús personalizada en español.
La dieta, alergias, gustos o nivel de cocina son campos opcionales, pero los ingredientes son obligatorios.

CONTEXTO DEL USUARIO:
- Ingredientes disponibles: {', '.join(ingredientes) if ingredientes else 'ninguno'}
- Dieta: {preferencias.get('dieta', 'omnivoro')}
- Alergias: {', '.join(preferencias.get('alergias', [])) if preferencias.get('alergias') else 'ninguna'}
- Gustos: {', '.join(preferencias.get('gustos', [])) if preferencias.get('gustos') else 'ninguno'}
- Nivel de cocina: {nivel_texto}
- Fecha de inicio de la semana: {fecha_inicio}

RECETAS DISPONIBLES (usa estos IDs para asignar):
{recetas_texto}

INSTRUCCIONES ESTRICTAS:
1. Genera una planificación para 7 días completos (de lunes a domingo)
2. Incluye TRES comidas por día: 'desayuno', 'almuerzo', 'cena'
3. Usa PRINCIPALMENTE ingredientes de la lista disponible
4. Respeta ESTRICTAMENTE las alergias y dieta del usuario
5. Asigna recetas existentes por su ID cuando sea posible
6. Varía los menús para evitar repetir platos consecutivos
7. Considera el balance nutricional y tiempos de preparación realistas
8. Adapta la complejidad al nivel de cocina del usuario
9. Devuelve SOLO JSON válido, sin texto adicional

FORMATO JSON REQUERIDO:
{{
  "semana": "{fecha_inicio}",
  "sugerencias": {{
    "YYYY-MM-DD": {{
      "desayuno": "ID_RECETA_O_NULL",
      "almuerzo": "ID_RECETA_O_NULL",
      "cena": "ID_RECETA_O_NULL"
    }},
    ...
  }}
}}

RESPUESTA (SOLO JSON, sin explicaciones):
"""
        return prompt

    # -------------------------
    # Helpers de extracción y parsing robusto
    # -------------------------
    def _extract_text_from_sdk_response(self, response) -> str:
        """
        Intenta extraer el texto humano desde diferentes estructuras de respuesta del SDK.
        Maneja: .text, .candidates[].content.parts[].text, .candidates[].content (str), .output, etc.
        """
        try:
            # 1) Atributo .text
            if hasattr(response, "text") and response.text:
                return response.text

            # 2) .candidates (lista de candidate objects)
            if hasattr(response, "candidates"):
                try:
                    candidates = getattr(response, "candidates")
                    if isinstance(candidates, (list, tuple)) and len(candidates) > 0:
                        first = candidates[0]
                        if isinstance(first, dict):
                            if "content" in first:
                                cont = first["content"]
                                if isinstance(cont, str):
                                    return cont
                                if isinstance(cont, list):
                                    parts = []
                                    for c in cont:
                                        if isinstance(c, dict):
                                            txt = c.get("text") or c.get("content")
                                            if isinstance(txt, str):
                                                parts.append(txt)
                                        elif isinstance(c, str):
                                            parts.append(c)
                                    if parts:
                                        return "\n".join(parts)
                                if isinstance(cont, dict) and "parts" in cont:
                                    pts = cont.get("parts") or []
                                    parts_text = []
                                    for p in pts:
                                        if isinstance(p, dict) and "text" in p:
                                            parts_text.append(p["text"])
                                        elif isinstance(p, str):
                                            parts_text.append(p)
                                    if parts_text:
                                        return "\n".join(parts_text)
                        else:
                            if hasattr(first, "content"):
                                cont = getattr(first, "content")
                                if isinstance(cont, str):
                                    return cont
                                try:
                                    parts = getattr(cont, "parts", None)
                                    if parts:
                                        texts = []
                                        for p in parts:
                                            if isinstance(p, dict) and "text" in p:
                                                texts.append(p["text"])
                                            elif hasattr(p, "text"):
                                                texts.append(getattr(p, "text"))
                                        if texts:
                                            return "\n".join(texts)
                                except Exception:
                                    pass
                            if hasattr(first, "text") and getattr(first, "text"):
                                return getattr(first, "text")
                            return str(first)
                except Exception:
                    pass

            # 3) .output (assistant v1 style)
            if hasattr(response, "output"):
                out = getattr(response, "output")
                try:
                    if isinstance(out, dict) and "content" in out:
                        content = out["content"]
                        if isinstance(content, str):
                            return content
                        if isinstance(content, list):
                            parts = []
                            for item in content:
                                if isinstance(item, dict):
                                    txt = item.get("text") or item.get("content")
                                    if isinstance(txt, str):
                                        parts.append(txt)
                                elif isinstance(item, str):
                                    parts.append(item)
                            if parts:
                                return "\n".join(parts)
                except Exception:
                    pass

            # 4) str(response) fallback
            try:
                s = str(response)
                return s
            except Exception:
                return ""
        except Exception as e:
            logger.exception("Error extrayendo texto del response SDK: %s", e)
            return ""

    def _is_truncated_response(self, response, texto: str) -> bool:
        """
        Intenta decidir si la respuesta está truncada:
        - finish_reason en candidates[0] == MAX_TOKENS (o contiene 'MAX_TOKENS')
        - o JSON detectado incompleto (falta ']' o '}' de cierre)
        """
        try:
            # 1) check finish_reason en candidates
            if hasattr(response, "candidates"):
                try:
                    candidates = getattr(response, "candidates")
                    if isinstance(candidates, (list, tuple)) and len(candidates) > 0:
                        c0 = candidates[0]
                        fr = None
                        if isinstance(c0, dict):
                            fr = c0.get("finish_reason") or c0.get("finishReason") or c0.get("finish")
                        else:
                            fr = getattr(c0, "finish_reason", None) or getattr(c0, "finishReason", None)
                        if fr:
                            if isinstance(fr, (str,)):
                                if "MAX_TOKENS" in fr.upper() or "MAXTOKENS" in fr.upper() or "MAX" in fr.upper():
                                    return True
                except Exception:
                    pass

            # 2) buscar en repr si SDK no expone el campo
            try:
                r = repr(response)
                if "MAX_TOKENS" in r or "finish_reason=MAX_TOKENS" in r or "finish_reason=MAX" in r:
                    return True
            except Exception:
                pass

            # 3) JSON truncado: extraer primer bloque y comprobar cierre
            try:
                js = self._extract_first_json(texto)
                if js is not None:
                    txt = js.strip()
                    if (txt.startswith("[") and not txt.endswith("]")) or (txt.startswith("{") and not txt.endswith("}")):
                        return True
            except Exception:
                pass

            return False
        except Exception as e:
            logger.exception("Error detectando truncamiento: %s", e)
            return False

    def _parsear_array_recetas_es(self, texto: str) -> List[Dict[str, Any]]:
        """Extrae el primer array JSON de recetas y normaliza campos en español."""
        try:
            json_str = self._extract_first_json(texto)
            if not json_str:
                return []
            data = json.loads(json_str)
            if not isinstance(data, list):
                return []
            normalized = []
            for r in data:
                receta = {
                    "nombre": r.get("nombre"),
                    "tiempo": int(r.get("tiempo")) if r.get("tiempo") is not None else None,
                    "calorias": int(r.get("calorias")) if r.get("calorias") is not None else None,
                    "nivel": int(r.get("nivel")) if r.get("nivel") is not None else 1,
                    "razon": r.get("razon") or "",
                    "emoji": r.get("emoji") or "🍽️",
                    "ingredientes": []
                }
                for ing in r.get("ingredientes", []):
                    receta["ingredientes"].append({
                        "nombre": ing.get("nombre") or ing.get("name"),
                        "cantidad": ing.get("cantidad") or ing.get("quantity") or 0,
                        "unidad": ing.get("unidad") or ing.get("unit") or "",
                        "emoji": ing.get("emoji"),
                        "en_inventario": bool(ing.get("en_inventario", True))
                    })
                normalized.append(receta)
            return normalized
        except Exception as e:
            logger.exception("Error _parsear_array_recetas_es: %s", e)
            return []

    def _parsear_pasos(self, texto: str) -> List[Dict[str, Any]]:
        """Parsea array de pasos JSON y normaliza a {n,instruccion,timer}"""
        try:
            json_str = self._extract_first_json(texto)
            if not json_str:
                return []
            parsed = json.loads(json_str)
            if not isinstance(parsed, list):
                return []
            pasos = []
            for p in parsed:
                n = p.get("n") or p.get("numero") or p.get("numero_paso")
                try:
                    n = int(n) if n is not None else None
                except Exception:
                    n = None
                instruccion = p.get("instruccion") or p.get("instruction") or p.get("texto") or ""
                timer = None
                if "timer" in p:
                    timer = p.get("timer")
                elif "temporizador_segundos" in p:
                    timer = p.get("temporizador_segundos")
                pasos.append({"n": n, "instruccion": instruccion, "timer": timer})
            pasos = [p for p in pasos if p["instruccion"]]
            pasos.sort(key=lambda x: (x["n"] if x["n"] is not None else 9999))
            return pasos
        except Exception as e:
            logger.exception("Error _parsear_pasos: %s", e)
            return []

    def _parsear_fallback_plaintext(self, texto: str) -> List[Dict[str, Any]]:
        """
        Intentar convertir texto plano con lista / YAML a JSON con heurísticas básicas.
        Esto ayuda cuando el modelo responde con formato 'nombre: X' o '- Nombre: X' etc.
        """
        try:
            lines = [l.strip() for l in texto.splitlines() if l.strip()]
            # buscar bloques que parezcan recetas: líneas que empiezan con nombre:, Nombre:, - Nombre:
            bloques = []
            current = []
            for ln in lines:
                if re.match(r'^(-\s*)?nombre\s*[:=]\s*', ln, re.IGNORECASE) or re.match(r'^- ', ln):
                    if current:
                        bloques.append(current)
                        current = []
                    current.append(ln)
                else:
                    if current:
                        current.append(ln)
            if current:
                bloques.append(current)

            resultados = []
            for blk in bloques:
                texto_blk = " ".join(blk)
                # heurística: extraer nombre, tiempo, calorias, nivel, emoji, ingredientes simples
                nombre_m = re.search(r'nombre\s*[:=]\s*["\']?([^,"\n]+)', texto_blk, re.IGNORECASE)
                tiempo_m = re.search(r'tiempo\s*[:=]\s*(\d+)', texto_blk, re.IGNORECASE)
                calor_m = re.search(r'calorias\s*[:=]\s*(\d+)', texto_blk, re.IGNORECASE)
                nivel_m = re.search(r'nivel\s*[:=]\s*(\d+)', texto_blk, re.IGNORECASE)
                emoji_m = re.search(r'emoji\s*[:=]\s*["\']?([^\s,"\']+)', texto_blk, re.IGNORECASE)

                nombre = nombre_m.group(1).strip() if nombre_m else None
                tiempo = int(tiempo_m.group(1)) if tiempo_m else None
                calorias = int(calor_m.group(1)) if calor_m else None
                nivel = int(nivel_m.group(1)) if nivel_m else 1
                emoji = emoji_m.group(1) if emoji_m else "🍽️"

                # ingredientes heurísticos: buscar por "ingredientes:" y luego items separados por comma
                ingredientes = []
                ingr_block = ""
                m_ing = re.search(r'ingredientes\s*[:=]\s*(.+)', texto_blk, re.IGNORECASE)
                if m_ing:
                    ingr_block = m_ing.group(1)
                if ingr_block:
                    parts = re.split(r',\s*|\s*;\s*|\n', ingr_block)
                    for p in parts:
                        p = p.strip()
                        if not p:
                            continue
                        q = re.search(r'(?P<cant>\d+(\.\d+)?)\s*(?P<unit>[a-zA-Z%]+)?\s*(?P<nombre>.+)', p)
                        if q:
                            nombre_ing = q.group('nombre').strip()
                            cantidad = float(q.group('cant'))
                            unidad = q.group('unit') or ''
                        else:
                            nombre_ing = p
                            cantidad = 0
                            unidad = ''
                        ingredientes.append({"nombre": nombre_ing, "cantidad": cantidad, "unidad": unidad, "emoji": None, "en_inventario": True})

                resultados.append({
                    "nombre": nombre or "Sin nombre",
                    "tiempo": tiempo or 0,
                    "calorias": calorias or 0,
                    "nivel": nivel,
                    "razon": "",
                    "emoji": emoji,
                    "ingredientes": ingredientes
                })

            # si no detectó bloques, intentar parsear como un único bloque
            if not resultados and lines:
                text_join = " ".join(lines[:40])
                m_nombre = re.search(r'([A-ZÁÉÍÓÚÑ][\w\s]+)\s+-\s+tiempo\s*[:=]\s*(\d+)', text_join, re.IGNORECASE)
                if m_nombre:
                    resultados.append({"nombre": m_nombre.group(1).strip(), "tiempo": int(m_nombre.group(2)), "calorias": 0, "nivel": 1, "razon": "", "emoji": "🍽️", "ingredientes": []})

            return resultados
        except Exception as e:
            logger.exception("Error _parsear_fallback_plaintext: %s", e)
            return []

    def _parsear_pasos_fallback_from_plaintext(self, texto: str) -> List[Dict[str, Any]]:
        """
        Fallback para convertir un texto de pasos (lista numerada o con guiones) a array de pasos.
        """
        try:
            lines = [l.strip() for l in texto.splitlines() if l.strip()]
            pasos = []
            n = 1
            for ln in lines:
                # ignorar encabezados JSON
                if re.match(r'^\s*\[|\{', ln):
                    continue
                m = re.match(r'^(?:\d+[\.\)]\s*|Paso\s*\d+\:?\s*|-+\s*)(.+)', ln, re.IGNORECASE)
                if m:
                    instr = m.group(1).strip()
                    # buscar timer en la misma línea (ej: 5 min, 300s)
                    t = None
                    tm = re.search(r'(\d+)\s*(s|sec|min|m[in]{0,2})', ln, re.IGNORECASE)
                    if tm:
                        val = int(tm.group(1))
                        unit = tm.group(2).lower()
                        if unit.startswith('m'):
                            t = val * 60
                        else:
                            t = val
                    pasos.append({"n": n, "instruccion": instr, "timer": t})
                    n += 1
                else:
                    if pasos:
                        pasos[-1]["instruccion"] += " " + ln
                    else:
                        pasos.append({"n": n, "instruccion": ln, "timer": None})
                        n += 1
            return pasos
        except Exception as e:
            logger.exception("Error _parsear_pasos_fallback_from_plaintext: %s", e)
            return []

    def _extract_first_json(self, text: str) -> Optional[str]:
        """Extrae el primer bloque JSON (array u objeto) que encuentre en el texto."""
        try:
            # Priorizar bloque ```json ... ```
            m = re.search(r'```json\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```', text, re.IGNORECASE)
            if m:
                return m.group(1)

            # Buscar primer '[' ... ']' balanceado (para arrays)
            start = text.find("[")
            if start != -1:
                depth = 0
                end = -1
                for i in range(start, len(text)):
                    if text[i] == "[":
                        depth += 1
                    elif text[i] == "]":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end != -1:
                    return text[start:end]

            # Buscar primer '{' ... '}' balanceado (objeto)
            start = text.find("{")
            if start != -1:
                depth = 0
                end = -1
                for i in range(start, len(text)):
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end != -1:
                    return text[start:end]

            return None
        except Exception as e:
            logger.exception("Error extrayendo JSON: %s", e)
            return None

    def _parsear_respuesta_planificacion(self, respuesta: str) -> Dict[str, Any]:
        """
        Parsear la respuesta de planificación semanal.
        Acepta respuestas con bloque ```json ... ``` o JSON plano.
        Si falla, devuelve el _planificacion_por_defecto.
        """
        try:
            json_str = self._extract_first_json(respuesta)
            if not json_str:
                raise ValueError("No se encontró JSON en la respuesta de planificación")

            planificacion = json.loads(json_str)
            if not isinstance(planificacion, dict) or "sugerencias" not in planificacion:
                raise ValueError("Formato de planificación inesperado (falta 'sugerencias')")

            # Validar que 'sugerencias' contenga 7 entradas (opcional)
            # No forzamos exactitud; simplemente devolvemos lo recibido si tiene la clave.
            return planificacion
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Error parseando respuesta de planificación: %s. Respuesta cruda: %.500s", e, respuesta)
            # fallback a planificación por defecto usando la fecha actual como inicio
            return self._planificacion_por_defecto(datetime.now().strftime("%Y-%m-%d"))
        except Exception as e:
            logger.exception("Error inesperado parseando planificación: %s", e)
            return self._planificacion_por_defecto(datetime.now().strftime("%Y-%m-%d"))

    # -------------------------
    # Valores por defecto y helpers de fallback
    # -------------------------
    def _recetas_por_defecto(self) -> List[Dict[str, Any]]:
        return [
            {
                "nombre": "Ensalada de Tomate",
                "tiempo": 10,
                "calorias": 150,
                "nivel": 1,
                "razon": "Receta básica usando ingredientes disponibles",
                "emoji": "🥗",
                "ingredientes": [
                    {"nombre": "Tomate", "cantidad": 2, "unidad": "unidades", "emoji": "🍅", "en_inventario": True},
                    {"nombre": "Aceite de Oliva", "cantidad": 1, "unidad": "cucharada", "emoji": "🫗", "en_inventario": True}
                ]
            }
        ]

    def _planificacion_por_defecto(self, fecha_inicio: str) -> Dict[str, Any]:
        """Planificación por defecto en caso de error"""
        from datetime import timedelta
        try:
            from modules.recipe.models import Receta
            recetas = Receta.query.limit(3).all()
            fecha = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            sugerencias = {}
            receta_ids = [r.id for r in recetas] if recetas else [None, None, None]
            for i in range(7):
                fecha_str = (fecha + timedelta(days=i)).strftime("%Y-%m-%d")
                sugerencias[fecha_str] = {
                    "desayuno": receta_ids[0] if len(receta_ids) > 0 else None,
                    "almuerzo": receta_ids[1] if len(receta_ids) > 1 else None,
                    "cena": receta_ids[2] if len(receta_ids) > 2 else None
                }
            return {"semana": fecha_inicio, "sugerencias": sugerencias}
        except Exception as e:
            logger.exception("Error creando planificación por defecto: %s", e)
            fecha = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            sugerencias = {}
            for i in range(7):
                fecha_str = (fecha + timedelta(days=i)).strftime("%Y-%m-%d")
                sugerencias[fecha_str] = {"desayuno": None, "almuerzo": None, "cena": None}
            return {"semana": fecha_inicio, "sugerencias": sugerencias}


# Instancia global del servicio (exportar para usar en otros módulos)
gemini_service = GeminiService()
