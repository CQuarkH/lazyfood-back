# api/tests/unit/conftest.py
"""
Configuración de pytest para tests unitarios.
Este archivo contiene fixtures compartidos para los tests.
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Set environment variables BEFORE any imports that might use them
# This is critical for module-level instantiations like gemini_service
def pytest_configure(config):
    """Hook que se ejecuta antes de la recolección de tests"""
    os.environ['GOOGLE_API_KEY'] = 'test_key_for_unit_tests'
    os.environ['GEMINI_MODEL'] = 'gemini-2.0-flash-exp'
    
    # Mock genai module globally to prevent actual API calls during collection
    mock_genai_patcher = patch('modules.ai.gemini_service.genai')
    mock_genai = mock_genai_patcher.start()
    
    # Configure the mock to return a mock client
    mock_client = Mock()
    mock_client.models = Mock()
    mock_genai.Client.return_value = mock_client
    mock_genai.types = Mock()
    
    # Store patcher to clean up later if needed
    config._mock_genai_patcher = mock_genai_patcher

# Agregar el directorio src al path para poder importar módulos
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_ingredients():
    """Fixture con ingredientes de ejemplo"""
    return ['tomate', 'cebolla', 'ajo', 'aceite de oliva', 'sal']


@pytest.fixture
def sample_recipe_data():
    """Fixture con datos de receta de ejemplo"""
    return {
        'nombre': 'Ensalada Mediterránea',
        'tiempo': 15,
        'calorias': 200,
        'nivel': 1,
        'emoji': '🥗',
        'razon': 'Receta saludable y rápida',
        'ingredientes': [
            {
                'nombre': 'tomate',
                'cantidad': 2,
                'unidad': 'unidades',
                'emoji': '🍅',
                'en_inventario': True
            },
            {
                'nombre': 'cebolla',
                'cantidad': 1,
                'unidad': 'unidad',
                'emoji': '🧅',
                'en_inventario': True
            }
        ]
    }


@pytest.fixture
def sample_steps_data():
    """Fixture con pasos de receta de ejemplo"""
    return [
        {
            'n': 1,
            'instruccion': 'Lavar y cortar los tomates en rodajas',
            'timer': None
        },
        {
            'n': 2,
            'instruccion': 'Picar la cebolla finamente',
            'timer': 120
        },
        {
            'n': 3,
            'instruccion': 'Mezclar todos los ingredientes',
            'timer': 60
        }
    ]


@pytest.fixture
def sample_recipe_list():
    """Fixture con lista de recetas de ejemplo"""
    return [
        {'id': 1, 'nombre': 'Pasta Carbonara'},
        {'id': 2, 'nombre': 'Ensalada César'},
        {'id': 3, 'nombre': 'Tortilla de Patatas'}
    ]
