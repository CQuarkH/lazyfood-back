import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import google.generativeai as genai
from PIL import Image
import io
from datetime import datetime
import logging
import json
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ingredients_parser import parse_gemini_response_with_coords
from ingredients_db import INGREDIENTS_DATABASE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurar Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MODEL = os.getenv("GEMINI_CV_MODEL", "gemini-2.0-flash")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(MODEL)
    logger.info("Modelo AI configurado")
else:
    model = None
    logger.warning("⚠️  GOOGLE_API_KEY no configurada")

# ============ MODELOS PYDANTIC ============

class BoundingBox(BaseModel):
    x: float  # Coordenada X del centro (0-1)
    y: float  # Coordenada Y del centro (0-1)
    width: float  # Ancho normalizado (0-1)
    height: float  # Alto normalizado (0-1)

class IngredientDetected(BaseModel):
    id: str
    name: str
    emoji: str
    category: str
    quantity: float
    unit: str
    state: str
    confidence: float = 0.95
    bounding_box: Optional[BoundingBox] = None  # NUEVO

class InventoryDetectionResponse(BaseModel):
    success: bool
    total_items: int
    detected_at: str
    inventory: List[IngredientDetected]
    categories: dict
    raw_detection: Optional[str] = None
    image_dimensions: Optional[Dict[str, int]] = None  # NUEVO

# ============ APP ============

app = FastAPI(
    title="LazyFood ML Service",
    description="Detección de ingredientes con Bounding Boxes",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def detect_with_gemini(image_bytes: bytes, max_retries: int = 3) -> tuple[str, tuple[int, int]]:
    """Detecta ingredientes con coordenadas - CON RETRY AUTOMÁTICO"""
    
    if not model:
        raise HTTPException(500, "GOOGLE_API_KEY no configurada")
    
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            # Cargar imagen y obtener dimensiones
            image = Image.open(io.BytesIO(image_bytes))
            image_dimensions = (image.width, image.height)
            
            # Prompt optimizado para ingredientes CON COORDENADAS
            prompt = """Analiza esta imagen e identifica TODOS los ingredientes alimenticios visibles.

Para cada ingrediente, proporciona:
1. Nombre específico del ingrediente en español
2. Cantidad aproximada (en gramos, ml, o unidades)
3. Ubicación aproximada en la imagen (bounding box)

IMPORTANTE: Responde SOLO con un JSON válido en este formato exacto:

{
  "ingredients": [
    {
      "name": "nombre del ingrediente",
      "quantity": número,
      "unit": "unidad (g, ml, unidades, tazas, etc)",
      "bounding_box": {
        "x": coordenada_x_centro_normalizada,
        "y": coordenada_y_centro_normalizada,
        "width": ancho_normalizado,
        "height": alto_normalizado
      }
    }
  ]
}

Las coordenadas deben ser valores entre 0 y 1, donde:
- (0, 0) = esquina superior izquierda
- (1, 1) = esquina inferior derecha
- x, y = centro del ingrediente
- width, height = tamaño relativo del área que ocupa

Ejemplo real:
{
  "ingredients": [
    {
      "name": "tomate",
      "quantity": 2,
      "unit": "unidades",
      "bounding_box": {"x": 0.25, "y": 0.3, "width": 0.2, "height": 0.25}
    },
    {
      "name": "queso mozzarella rallado",
      "quantity": 300,
      "unit": "g",
      "bounding_box": {"x": 0.7, "y": 0.5, "width": 0.3, "height": 0.35}
    }
  ]
}

Analiza la imagen y responde ÚNICAMENTE con el JSON, sin texto adicional antes o después."""

            logger.info(f"🤖 Detectando ingredientes... (Intento {attempt}/{max_retries})")
            
            # Generar respuesta
            response = model.generate_content([prompt, image])
            
            logger.info("✅ Modelo AI respondió exitosamente")
            
            return response.text, image_dimensions
            
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            # Verificar si es error de rate limit
            is_rate_limit = any(keyword in error_msg for keyword in [
                'quota', 'rate limit', 'too many requests', 'resource exhausted',
                '429', 'overloaded'
            ])
            
            if is_rate_limit and attempt < max_retries:
                # Espera exponencial: 2s, 4s, 8s
                wait_time = 2 ** attempt
                logger.warning(f"⚠️ Rate limit detectado. Reintentando en {wait_time}s... ({attempt}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue
            
            # Si no es rate limit o ya agotamos reintentos
            if attempt == max_retries:
                logger.error(f"❌ Error después de {max_retries} intentos: {str(e)}")
                raise HTTPException(500, f"Error procesando con Modelo AI después de {max_retries} intentos: {str(e)}")
            
            # Para otros errores, reintentamos con menos espera
            logger.warning(f"⚠️ Error en intento {attempt}: {str(e)}. Reintentando...")
            await asyncio.sleep(1)
    
    # Si llegamos aquí, algo salió mal
    raise HTTPException(500, f"Error procesando imagen: {str(last_error)}")

# ============ ENDPOINTS ============

@app.get("/")
async def root():
    return {
        "service": "LazyFood ML Service",
        "version": "2.0.0",
        "features": ["ingredient_detection", "bounding_boxes", "quantity_estimation"],
        "api_configured": model is not None,
        "status": "running"
    }

@app.post("/api/v1/detect-inventory", response_model=InventoryDetectionResponse)
async def detect_inventory(file: UploadFile = File(...)):
    try:
        logger.info(f"📸 Procesando: {file.filename}")
        
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "Debe ser una imagen (JPG, PNG, WebP)")
        
        contents = await file.read()
        
        # Detectar con Gemini (ahora retorna también dimensiones)
        raw_answer, image_dims = await detect_with_gemini(contents)
        logger.info(f"📐 Dimensiones imagen: {image_dims[0]}x{image_dims[1]}")
        logger.info(f"📝 Respuesta: {raw_answer[:300]}...")
        
        # Parsear CON coordenadas
        detected_items = parse_gemini_response_with_coords(raw_answer)
        logger.info(f"✅ {len(detected_items)} ingredientes detectados")
        
        # Construir respuesta
        inventory = []
        for item in detected_items:
            bbox_data = item.get('bounding_box')
            bbox = BoundingBox(**bbox_data) if bbox_data else None
            
            inventory.append(IngredientDetected(
                id=item['id'],
                name=item['name'],
                emoji=item['emoji'],
                category=item['category'],
                quantity=item['quantity'],
                unit=item['unit'],
                state=item.get('state', 'detected'),
                confidence=0.95,
                bounding_box=bbox
            ))
        
        # Agrupar por categoría
        categories = {}
        for item in inventory:
            cat = item.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item.dict())
        
        return InventoryDetectionResponse(
            success=True,
            total_items=len(inventory),
            detected_at=datetime.now().isoformat(),
            inventory=inventory,
            categories=categories,
            raw_detection=raw_answer,
            image_dimensions={"width": image_dims[0], "height": image_dims[1]}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")

@app.get("/api/v1/ingredients")
async def get_ingredients_list():
    ingredients = []
    for id_en, data in INGREDIENTS_DATABASE.items():
        ingredients.append({
            "id": id_en,
            "name": data["es"],
            "name_en": id_en,
            "emoji": data["emoji"],
            "category": data["category_es"],
            "category_en": data["category"],
            "unit": data["unit_es"],
            "unit_en": data["unit"]
        })
    return {"total": len(ingredients), "ingredients": ingredients}

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "features": ["bounding_boxes", "quantity_estimation"],
        "api_configured": model is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, log_level="info")