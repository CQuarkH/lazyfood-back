from datetime import datetime

from google import genai
from google.genai import types
import json
import re
from core.config import Config
from typing import List, Dict, Any


class GeminiService:
    """Servicio para interactuar con Gemini AI"""

    def __init__(self):
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
        self.model_config = types.GenerateContentConfig(temperature=0)
        print(f"✓ Gemini AI inicializado con modelo: {self.model_name}")

    def generar_recetas(self, ingredientes: List[str], preferencias: Dict[str, Any], nivel_cocina: int) -> List[
        Dict[str, Any]]:
        """
        Generar recetas personalizadas usando Gemini AI

        Args:
            ingredientes: Lista de ingredientes disponibles
            preferencias: Diccionario con dieta, alergias, gustos
            nivel_cocina: 1 (principiante), 2 (intermedio), 3 (avanzado)

        Returns:
            Lista de recetas en formato estructurado
        """
        try:
            prompt = self._construir_prompt(ingredientes, preferencias, nivel_cocina)
            response = self.model.generate_content(model=self.model_name, contents= prompt, config= self.model_config)

            print("Gemini response:")
            print(response.text)

            # Parsear la respuesta JSON
            recetas = self._parsear_respuesta(response.text)
            print("Recipes Parser:")
            print(recetas)
            return recetas

        except Exception as e:
            print(f"Error generando recetas con Gemini: {str(e)}")
            # En caso de error, devolver recetas de ejemplo
            return self._recetas_por_defecto()

    def _construir_prompt(self, ingredientes: List[str], preferencias: Dict[str, Any], nivel_cocina: int) -> str:
        """Construir el prompt para Gemini"""

        nivel_texto = {1: "principiante", 2: "intermedio", 3: "avanzado"}.get(nivel_cocina, "principiante")

        prompt = f"""
Eres un chef experto y nutricionista. Genera 3 recetas de cocina personalizadas en español.

CONTEXTO:
- Ingredientes disponibles: {', '.join(ingredientes)}
- Dieta: {preferencias.get('dieta', 'omnivoro')}
- Alergias: {', '.join(preferencias.get('alergias', []))}
- Gustos: {', '.join(preferencias.get('gustos', []))}
- Nivel de cocina: {nivel_texto}

INSTRUCCIONES ESTRICTAS:
1. Genera EXACTAMENTE 3 recetas
2. Usa SOLO ingredientes de la lista disponible
3. Respeta las alergias y dieta
4. Adapta la dificultad al nivel de cocina
5. Devuelve SOLO JSON válido, sin texto adicional

FORMATO JSON REQUERIDO (array de objetos):
[
  {{
    "nombre": "Nombre de la receta",
    "tiempo": minutos enteros,
    "calorias": calorías enteras por porción,
    "nivel": 1, 2 o 3 (fácil, medio, difícil),
    "razon": "Explicación breve de por qué se recomienda",
    "ingredientes": [
      {{
        "nombre": "nombre ingrediente",
        "cantidad": "cantidad con unidad",
        "foto": "https://cdn.lazyfood.com/ingredientes/[nombre].jpg",
        "en_inventario": true
      }}
    ],
    "pasos": [
      {{
        "n": número de paso,
        "instruccion": "Instrucción clara",
        "timer": segundos o null
      }}
    ]
  }}
]

IMPORTANTE:
- Para 'foto' en ingredientes, usa siempre el formato: https://cdn.lazyfood.com/ingredientes/[nombre].jpg
- Para 'razon', explica brevemente: "Coincide X% con tus ingredientes y es apta para [dieta]"
- Los tiempos de preparación deben ser realistas
- Los pasos deben ser claros y secuenciales

RESPUESTA (SOLO JSON):
"""
        return prompt

    def _parsear_respuesta(self, respuesta: str) -> List[Dict[str, Any]]:
        """Parsear la respuesta de Gemini para extraer el JSON"""
        try:
            # Limpiar la respuesta - buscar JSON entre ```
            json_match = re.search(r'```json\s*(.*?)\s*```', respuesta, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Si no hay ```, buscar el primer [ y último ]
                start = respuesta.find('[')
                end = respuesta.rfind(']') + 1
                if start != -1 and end != 0:
                    json_str = respuesta[start:end]
                else:
                    json_str = respuesta

            # Limpiar posibles caracteres extraños
            json_str = json_str.strip()

            # Parsear JSON
            recetas = json.loads(json_str)

            # Validar estructura básica
            if not isinstance(recetas, list):
                raise ValueError("La respuesta no es una lista")

            return recetas

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parseando respuesta de Gemini: {e}")
            print(f"Respuesta cruda: {respuesta}")
            return self._recetas_por_defecto()

    def _recetas_por_defecto(self) -> List[Dict[str, Any]]:
        """Recetas por defecto en caso de error"""
        return [
            {
                "nombre": "Ensalada de Tomate",
                "tiempo": 10,
                "calorias": 150,
                "nivel": 1,
                "razon": "Receta básica usando ingredientes disponibles",
                "ingredientes": [
                    {
                        "nombre": "tomate",
                        "cantidad": "2 unidades",
                        "foto": "https://cdn.lazyfood.com/ingredientes/tomate.jpg",
                        "en_inventario": True
                    },
                    {
                        "nombre": "aceite de oliva",
                        "cantidad": "1 cucharada",
                        "foto": "https://cdn.lazyfood.com/ingredientes/aceite-oliva.jpg",
                        "en_inventario": True
                    }
                ],
                "pasos": [
                    {
                        "n": 1,
                        "instruccion": "Lavar y cortar los tomates en rodajas",
                        "timer": None
                    },
                    {
                        "n": 2,
                        "instruccion": "Aliñar con aceite de oliva y sal",
                        "timer": None
                    }
                ]
            }
        ]

    def generar_planificacion_semanal(self, ingredientes: List[str], preferencias: Dict[str, Any],
                                      nivel_cocina: int, recetas_sugeridas: List[Dict[str, Any]],
                                      fecha_inicio: str) -> Dict[str, Any]:
        """
        Generar planificación semanal de menús usando Gemini AI

        Args:
            ingredientes: Lista de ingredientes disponibles
            preferencias: Diccionario con dieta, alergias, gustos
            nivel_cocina: 1 (principiante), 2 (intermedio), 3 (avanzado)
            recetas_sugeridas: Lista de recetas previamente sugeridas
            fecha_inicio: Fecha de inicio de la semana (YYYY-MM-DD)

        Returns:
            Diccionario con la planificación semanal
        """
        try:
            prompt = self._construir_prompt_planificacion(ingredientes, preferencias, nivel_cocina, recetas_sugeridas,
                                                          fecha_inicio)
            response = self.model.generate_content(model=self.model_name, contents= prompt, config= self.model_config)

            print("Gemini response:")
            print(response.text)

            # Parsear la respuesta JSON
            planificacion = self._parsear_respuesta_planificacion(response.text)

            print("Planner parser:")
            print(planificacion)
            return planificacion

        except Exception as e:
            print(f"Error generando planificación con Gemini: {str(e)}")
            # En caso de error, devolver planificación por defecto
            return self._planificacion_por_defecto(fecha_inicio)

    def _construir_prompt_planificacion(self, ingredientes: List[str], preferencias: Dict[str, Any],
                                        nivel_cocina: int, recetas_sugeridas: List[Dict[str, Any]],
                                        fecha_inicio: str) -> str:
        """Construir el prompt para la planificación semanal"""

        nivel_texto = {1: "principiante", 2: "intermedio", 3: "avanzado"}.get(nivel_cocina, "principiante")

        # Formatear recetas sugeridas para el prompt
        recetas_texto = ""
        for receta in recetas_sugeridas[:10]:  # Usar solo las 10 primeras
            recetas_texto += f"- {receta['nombre']} (ID: {receta['id']}, Tiempo: {receta['tiempo']}min, Calorías: {receta['calorias']}, Nivel: {receta['nivel']})\n"

        prompt = f"""
Eres un nutricionista y chef experto. Genera una planificación semanal de menús personalizada en español.

CONTEXTO DEL USUARIO:
- Ingredientes disponibles: {', '.join(ingredientes)}
- Dieta: {preferencias.get('dieta', 'omnivoro')}
- Alergias: {', '.join(preferencias.get('alergias', []))}
- Gustos: {', '.join(preferencias.get('gustos', []))}
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
      "desayuno": ID_RECETA_O_NULL,
      "almuerzo": ID_RECETA_O_NULL,
      "cena": ID_RECETA_O_NULL
    }},
    ... (para los 7 días siguientes)
  }}
}}

REGLAS IMPORTANTES:
- Usa {fecha_inicio} como lunes y calcula los 6 días siguientes
- Si no hay receta adecuada para una comida, usa null
- Prioriza recetas que usen ingredientes disponibles
- Considera que el desayuno suele ser más simple que almuerzo/cena
- Incluye variedad: diferentes tipos de proteínas, verduras, etc.

RESPUESTA (SOLO JSON, sin explicaciones):
"""
        return prompt

    def _parsear_respuesta_planificacion(self, respuesta: str) -> Dict[str, Any]:
        """Parsear la respuesta de Gemini para extraer el JSON de planificación"""
        try:
            # Limpiar la respuesta - buscar JSON entre ```
            json_match = re.search(r'```json\s*(.*?)\s*```', respuesta, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Si no hay ```, buscar el primer { y último }
                start = respuesta.find('{')
                end = respuesta.rfind('}') + 1
                if start != -1 and end != 0:
                    json_str = respuesta[start:end]
                else:
                    json_str = respuesta

            # Limpiar posibles caracteres extraños
            json_str = json_str.strip()

            # Parsear JSON
            planificacion = json.loads(json_str)

            # Validar estructura básica
            if not isinstance(planificacion, dict) or 'sugerencias' not in planificacion:
                raise ValueError("La respuesta no tiene el formato esperado")

            return planificacion

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parseando respuesta de planificación: {e}")
            print(f"Respuesta cruda: {respuesta}")
            return self._planificacion_por_defecto(datetime.now().strftime('%Y-%m-%d'))

    def _planificacion_por_defecto(self, fecha_inicio: str) -> Dict[str, Any]:
        """Planificación por defecto en caso de error"""
        from datetime import datetime, timedelta

        try:
            # Obtener algunas recetas básicas de la base de datos
            from core.database import db
            from modules.recipe.models import Receta

            with db.session() as session:
                recetas = session.query(Receta).limit(3).all()

                # Generar 7 días a partir de la fecha de inicio
                fecha = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                sugerencias = {}

                receta_ids = [r.id for r in recetas] if recetas else [None, None, None]

                for i in range(7):
                    fecha_str = (fecha + timedelta(days=i)).strftime('%Y-%m-%d')
                    sugerencias[fecha_str] = {
                        "desayuno": receta_ids[0] if len(receta_ids) > 0 else None,
                        "almuerzo": receta_ids[1] if len(receta_ids) > 1 else None,
                        "cena": receta_ids[2] if len(receta_ids) > 2 else None
                    }

                return {
                    "semana": fecha_inicio,
                    "sugerencias": sugerencias
                }
        except Exception as e:
            print(f"Error creando planificación por defecto: {e}")
            # Planificación mínima como último recurso
            fecha = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            sugerencias = {}
            for i in range(7):
                fecha_str = (fecha + timedelta(days=i)).strftime('%Y-%m-%d')
                sugerencias[fecha_str] = {
                    "desayuno": None,
                    "almuerzo": None,
                    "cena": None
                }
            return {
                "semana": fecha_inicio,
                "sugerencias": sugerencias
            }


# Instancia global del servicio
gemini_service = GeminiService()