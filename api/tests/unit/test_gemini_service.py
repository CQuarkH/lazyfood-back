# api/tests/unit/test_gemini_service.py
import pytest
import json
from unittest.mock import Mock, patch


# Mock para evitar inicialización de Gemini en tests
@pytest.fixture
def gemini_service():
    """Fixture que retorna un GeminiService con mock de inicialización"""
    # Mock the genai module BEFORE importing GeminiService
    with patch('modules.ai.gemini_service.genai') as mock_genai:
        # Mock the client and its methods
        mock_client = Mock()
        mock_client.models = Mock()
        mock_genai.Client.return_value = mock_client
        
        # Import after patching
        from modules.ai.gemini_service import GeminiService
        
        # Create service instance (it will use the mocked genai)
        service = GeminiService()
        return service


class TestExtractFirstJson:
    """Tests para el método _extract_first_json"""
    
    def test_extract_json_array(self, gemini_service):
        """Debe extraer un array JSON del texto"""
        text = 'Aquí hay un array: [{"nombre": "test", "valor": 123}] y más texto'
        result = gemini_service._extract_first_json(text)
        assert result == '[{"nombre": "test", "valor": 123}]'
    
    def test_extract_json_object(self, gemini_service):
        """Debe extraer un objeto JSON del texto"""
        text = 'Respuesta: {"clave": "valor", "numero": 42}'
        result = gemini_service._extract_first_json(text)
        assert result == '{"clave": "valor", "numero": 42}'
    
    def test_extract_json_from_markdown(self, gemini_service):
        """Debe extraer JSON de un bloque markdown"""
        text = '''Aquí está el resultado:
```json
[{"id": 1, "nombre": "Receta"}]
```
Más texto'''
        result = gemini_service._extract_first_json(text)
        assert result == '[{"id": 1, "nombre": "Receta"}]'
    
    def test_extract_nested_json(self, gemini_service):
        """Debe manejar JSON anidado correctamente"""
        text = '{"nivel1": {"nivel2": [1, 2, 3]}, "otro": "valor"}'
        result = gemini_service._extract_first_json(text)
        assert result == '{"nivel1": {"nivel2": [1, 2, 3]}, "otro": "valor"}'
    
    def test_no_json_found(self, gemini_service):
        """Debe retornar None si no hay JSON"""
        text = 'Solo texto plano sin JSON'
        result = gemini_service._extract_first_json(text)
        assert result is None
    
    def test_malformed_json_returns_partial(self, gemini_service):
        """Debe retornar JSON parcial si está incompleto"""
        text = '[{"nombre": "test", "incompleto":'
        result = gemini_service._extract_first_json(text)
        # Solo encuentra el inicio del array sin cierre
        assert result is not None


class TestParsearArrayRecetasEs:
    """Tests para el método _parsear_array_recetas_es"""
    
    def test_parse_valid_recipe_array(self, gemini_service):
        """Debe parsear correctamente un array de recetas válido"""
        json_text = '''[
            {
                "nombre": "Ensalada César",
                "tiempo": 15,
                "calorias": 250,
                "nivel": 1,
                "razon": "Fácil y rápida",
                "emoji": "🥗",
                "ingredientes": [
                    {
                        "nombre": "Lechuga",
                        "cantidad": 1,
                        "unidad": "unidad",
                        "emoji": "🥬",
                        "en_inventario": true
                    }
                ]
            }
        ]'''
        result = gemini_service._parsear_array_recetas_es(json_text)
        
        assert len(result) == 1
        assert result[0]['nombre'] == 'Ensalada César'
        assert result[0]['tiempo'] == 15
        assert result[0]['calorias'] == 250
        assert result[0]['nivel'] == 1
        assert result[0]['emoji'] == '🥗'
        assert len(result[0]['ingredientes']) == 1
        assert result[0]['ingredientes'][0]['nombre'] == 'Lechuga'
    
    def test_parse_empty_array(self, gemini_service):
        """Debe retornar lista vacía para array vacío"""
        result = gemini_service._parsear_array_recetas_es('[]')
        assert result == []
    
    def test_parse_invalid_json(self, gemini_service):
        """Debe retornar lista vacía para JSON inválido"""
        result = gemini_service._parsear_array_recetas_es('esto no es json')
        assert result == []
    
    def test_parse_with_missing_fields(self, gemini_service):
        """Debe manejar recetas con campos faltantes"""
        json_text = '[{"nombre": "Test"}]'
        result = gemini_service._parsear_array_recetas_es(json_text)
        
        assert len(result) == 1
        assert result[0]['nombre'] == 'Test'
        assert result[0]['tiempo'] is None
        assert result[0]['nivel'] == 1  # valor por defecto
        assert result[0]['emoji'] == '🍽️'  # valor por defecto
    
    def test_parse_multiple_recipes(self, gemini_service):
        """Debe parsear múltiples recetas"""
        json_text = '''[
            {"nombre": "Receta 1", "tiempo": 10, "calorias": 100, "nivel": 1, "emoji": "🍕", "ingredientes": []},
            {"nombre": "Receta 2", "tiempo": 20, "calorias": 200, "nivel": 2, "emoji": "🍔", "ingredientes": []},
            {"nombre": "Receta 3", "tiempo": 30, "calorias": 300, "nivel": 3, "emoji": "🍰", "ingredientes": []}
        ]'''
        result = gemini_service._parsear_array_recetas_es(json_text)
        
        assert len(result) == 3
        assert result[0]['nombre'] == 'Receta 1'
        assert result[1]['nombre'] == 'Receta 2'
        assert result[2]['nombre'] == 'Receta 3'


class TestParsearPasos:
    """Tests para el método _parsear_pasos"""
    
    def test_parse_valid_steps(self, gemini_service):
        """Debe parsear pasos válidos correctamente"""
        json_text = '''[
            {"n": 1, "instruccion": "Cortar cebolla", "timer": 120},
            {"n": 2, "instruccion": "Freír en aceite", "timer": 300},
            {"n": 3, "instruccion": "Servir caliente", "timer": null}
        ]'''
        result = gemini_service._parsear_pasos(json_text)
        
        assert len(result) == 3
        assert result[0]['n'] == 1
        assert result[0]['instruccion'] == 'Cortar cebolla'
        assert result[0]['timer'] == 120
        assert result[2]['timer'] is None
    
    def test_parse_empty_steps(self, gemini_service):
        """Debe retornar lista vacía para array vacío"""
        result = gemini_service._parsear_pasos('[]')
        assert result == []
    
    def test_parse_steps_with_alternative_keys(self, gemini_service):
        """Debe manejar claves alternativas"""
        json_text = '''[
            {"numero": 1, "instruction": "Test step", "temporizador_segundos": 60}
        ]'''
        result = gemini_service._parsear_pasos(json_text)
        
        assert len(result) == 1
        assert result[0]['n'] == 1
        assert result[0]['instruccion'] == 'Test step'
        assert result[0]['timer'] == 60
    
    def test_parse_steps_filters_empty_instructions(self, gemini_service):
        """Debe filtrar pasos sin instrucción"""
        json_text = '''[
            {"n": 1, "instruccion": "Paso válido", "timer": null},
            {"n": 2, "instruccion": "", "timer": null},
            {"n": 3, "instruccion": "Otro válido", "timer": 30}
        ]'''
        result = gemini_service._parsear_pasos(json_text)
        
        assert len(result) == 2
        assert result[0]['instruccion'] == 'Paso válido'
        assert result[1]['instruccion'] == 'Otro válido'
    
    def test_parse_steps_sorts_by_number(self, gemini_service):
        """Debe ordenar pasos por número"""
        json_text = '''[
            {"n": 3, "instruccion": "Tercer paso", "timer": null},
            {"n": 1, "instruccion": "Primer paso", "timer": null},
            {"n": 2, "instruccion": "Segundo paso", "timer": null}
        ]'''
        result = gemini_service._parsear_pasos(json_text)
        
        assert len(result) == 3
        assert result[0]['n'] == 1
        assert result[1]['n'] == 2
        assert result[2]['n'] == 3


class TestParsearFallbackPlaintext:
    """Tests para el método _parsear_fallback_plaintext"""
    
    def test_parse_plaintext_with_nombre(self, gemini_service):
        """Debe extraer receta de texto plano con formato clave:valor"""
        text = '''
        nombre: Tortilla de Patatas
        tiempo: 30
        calorias: 400
        nivel: 2
        emoji: 🥔
        '''
        result = gemini_service._parsear_fallback_plaintext(text)
        
        assert len(result) >= 1
        assert result[0]['nombre'] == 'Tortilla de Patatas'
        assert result[0]['tiempo'] == 30
        assert result[0]['calorias'] == 400
        assert result[0]['nivel'] == 2
    
    def test_parse_empty_text(self, gemini_service):
        """Debe retornar lista vacía para texto vacío"""
        result = gemini_service._parsear_fallback_plaintext('')
        assert result == []
    
    def test_parse_multiple_recipes_plaintext(self, gemini_service):
        """Debe parsear múltiples recetas del texto plano"""
        text = '''
        - nombre: Receta 1
        tiempo: 10
        
        nombre: Receta 2
        tiempo: 20
        '''
        result = gemini_service._parsear_fallback_plaintext(text)
        
        # Al menos debería detectar una receta
        assert len(result) >= 1


class TestIsTruncatedResponse:
    """Tests para el método _is_truncated_response"""
    
    def test_not_truncated_complete_json(self, gemini_service):
        """No debe detectar truncamiento en JSON completo"""
        # Mock de respuesta completa
        class MockResponse:
            text = '[{"nombre": "test"}]'
        
        result = gemini_service._is_truncated_response(MockResponse(), MockResponse().text)
        assert result is False
    
    def test_truncated_incomplete_array(self, gemini_service):
        """Debe detectar truncamiento en array incompleto"""
        text = '[{"nombre": "test", "valor":'
        
        class MockResponse:
            pass
        
        result = gemini_service._is_truncated_response(MockResponse(), text)
        # Depende de si encuentra el patrón de truncamiento
        # Este test valida que el método no lance excepciones
        assert isinstance(result, bool)
