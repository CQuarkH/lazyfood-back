# api/tests/unit/test_recommendation_service.py
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def recommendation_service():
    """Fixture que retorna un RecommendationService sin dependencias de DB"""
    with patch('modules.recipe.recommendation_service.gemini_service'):
        from modules.recipe.recommendation_service import RecommendationService
        service = RecommendationService()
        return service


class TestCalcularCoincidencia:
    """Tests para el método _calcular_coincidencia"""
    
    def test_coincidencia_100_percent(self, recommendation_service):
        """Debe calcular 100% cuando todos los ingredientes coinciden"""
        ingredientes_usuario = ['tomate', 'cebolla', 'aceite']
        receta = {
            'ingredientes': [
                {'nombre': 'tomate', 'cantidad': 2},
                {'nombre': 'cebolla', 'cantidad': 1},
                {'nombre': 'aceite', 'cantidad': 1}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 100.0
    
    def test_coincidencia_50_percent(self, recommendation_service):
        """Debe calcular 50% cuando la mitad coincide"""
        ingredientes_usuario = ['tomate', 'cebolla']
        receta = {
            'ingredientes': [
                {'nombre': 'tomate', 'cantidad': 2},
                {'nombre': 'ajo', 'cantidad': 1}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 50.0
    
    def test_coincidencia_0_percent(self, recommendation_service):
        """Debe calcular 0% cuando no hay coincidencias"""
        ingredientes_usuario = ['tomate', 'cebolla']
        receta = {
            'ingredientes': [
                {'nombre': 'lechuga', 'cantidad': 1},
                {'nombre': 'zanahoria', 'cantidad': 2}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 0.0
    
    def test_coincidencia_empty_user_ingredients(self, recommendation_service):
        """Debe retornar 0% si el usuario no tiene ingredientes"""
        ingredientes_usuario = []
        receta = {
            'ingredientes': [
                {'nombre': 'tomate', 'cantidad': 2}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 0.0
    
    def test_coincidencia_empty_recipe_ingredients(self, recommendation_service):
        """Debe retornar 0% si la receta no tiene ingredientes"""
        ingredientes_usuario = ['tomate', 'cebolla']
        receta = {'ingredientes': []}
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 0.0
    
    def test_coincidencia_no_ingredients_key(self, recommendation_service):
        """Debe retornar 0% si la receta no tiene clave 'ingredientes'"""
        ingredientes_usuario = ['tomate']
        receta = {}
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 0.0
    
    def test_coincidencia_case_insensitive(self, recommendation_service):
        """Debe hacer matching case-insensitive"""
        ingredientes_usuario = ['TOMATE', 'Cebolla']
        receta = {
            'ingredientes': [
                {'nombre': 'tomate', 'cantidad': 2},
                {'nombre': 'cebolla', 'cantidad': 1}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 100.0
    
    def test_coincidencia_partial_name_match(self, recommendation_service):
        """Debe hacer matching parcial de nombres"""
        ingredientes_usuario = ['tomate cherry', 'aceite de oliva']
        receta = {
            'ingredientes': [
                {'nombre': 'tomate', 'cantidad': 2},
                {'nombre': 'aceite', 'cantidad': 1}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 100.0
    
    def test_coincidencia_whitespace_trimming(self, recommendation_service):
        """Debe ignorar espacios en blanco"""
        ingredientes_usuario = ['  tomate  ', '  cebolla  ']
        receta = {
            'ingredientes': [
                {'nombre': '  tomate  ', 'cantidad': 2},
                {'nombre': 'cebolla', 'cantidad': 1}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 100.0
    
    def test_coincidencia_33_percent(self, recommendation_service):
        """Debe calcular correctamente porcentaje con decimales"""
        ingredientes_usuario = ['tomate']
        receta = {
            'ingredientes': [
                {'nombre': 'tomate', 'cantidad': 1},
                {'nombre': 'cebolla', 'cantidad': 1},
                {'nombre': 'ajo', 'cantidad': 1}
            ]
        }
        
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        # 1/3 = 33.33... debe redondear a 2 decimales
        assert porcentaje == 33.33
    
    def test_coincidencia_multiple_matches_per_ingredient(self, recommendation_service):
        """Solo debe contar una vez cada ingrediente de la receta"""
        ingredientes_usuario = ['tomate', 'tomate cherry', 'tomate verde']
        receta = {
            'ingredientes': [
                {'nombre': 'tomate', 'cantidad': 2}
            ]
        }
        
        # Aunque el usuario tiene 3 tipos de tomate, solo cuenta 1 match
        porcentaje = recommendation_service._calcular_coincidencia(ingredientes_usuario, receta)
        assert porcentaje == 100.0
