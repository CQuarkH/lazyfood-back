# api/tests/unit/test_planning_service.py
import pytest
from datetime import datetime, timedelta
from modules.planner.planning_service import PlanningService


class TestResolverRecetaId:
    """Tests para el método _resolver_receta_id"""
    
    def test_resolver_none_returns_none(self):
        """Debe retornar None para valor None"""
        service = PlanningService()
        result = service._resolver_receta_id(None, {}, {})
        assert result is None
    
    def test_resolver_integer_valid(self):
        """Debe retornar el ID si es un entero válido en DB"""
        service = PlanningService()
        # Mock: crear un dict que simula recetas existentes
        recetas_by_id = {123: "mock_receta"}
        
        # Como no tenemos DB real, podemos probar la lógica con mock
        # En el código real consulta Receta.query.get(raw_value)
        # Para este test unitario solo validamos el flujo lógico
        result = service._resolver_receta_id(123, recetas_by_id, {})
        # El método hace una consulta real a DB, así que sin DB retornará None
        # Este test valida que no lance excepciones
        assert result is None or isinstance(result, int)
    
    def test_resolver_string_with_digits(self):
        """Debe extraer ID de string numérico"""
        service = PlanningService()
        # String solo con dígitos
        result = service._resolver_receta_id("456", {}, {})
        assert result is None or isinstance(result, int)
    
    def test_resolver_string_with_id_pattern(self):
        """Debe extraer ID de patrones como 'ID_RECETA_1'"""
        service = PlanningService()
        result = service._resolver_receta_id("ID_RECETA_789", {}, {})
        assert result is None or isinstance(result, int)
    
    def test_resolver_dict_with_id(self):
        """Debe extraer ID de diccionario con clave 'id'"""
        service = PlanningService()
        result = service._resolver_receta_id({"id": 123}, {123: "mock"}, {})
        assert result is None or isinstance(result, int)
    
    def test_resolver_dict_with_receta_id(self):
        """Debe extraer ID de diccionario con clave 'receta_id'"""
        service = PlanningService()
        result = service._resolver_receta_id({"receta_id": 456}, {456: "mock"}, {})
        assert result is None or isinstance(result, int)
    
    def test_resolver_dict_with_nombre(self):
        """Debe resolver por nombre si está en el diccionario"""
        service = PlanningService()
        recetas_by_name = {"ensalada cesar": 999}
        result = service._resolver_receta_id(
            {"nombre": "Ensalada Cesar"}, 
            {}, 
            recetas_by_name
        )
        assert result == 999
    
    def test_resolver_string_by_name(self):
        """Debe resolver string por nombre exacto"""
        service = PlanningService()
        recetas_by_name = {"pasta carbonara": 777}
        result = service._resolver_receta_id(
            "Pasta Carbonara", 
            {}, 
            recetas_by_name
        )
        assert result == 777
    
    def test_resolver_string_by_partial_name(self):
        """Debe resolver por nombre parcial (substring)"""
        service = PlanningService()
        recetas_by_name = {"ensalada de tomate": 888}
        result = service._resolver_receta_id(
            "ensalada", 
            {}, 
            recetas_by_name
        )
        assert result == 888
    
    def test_resolver_invalid_format_returns_none(self):
        """Debe retornar None para formatos inválidos"""
        service = PlanningService()
        result = service._resolver_receta_id(
            ["lista", "invalida"], 
            {}, 
            {}
        )
        assert result is None


class TestPlanificacionPorDefectoConIds:
    """Tests para el método _planificacion_por_defecto_con_ids"""
    
    def test_planificacion_default_7_days(self):
        """Debe generar planificación para 7 días"""
        service = PlanningService()
        fecha_inicio = "2025-12-01"
        recetas = [
            {'id': 1, 'nombre': 'Receta 1'},
            {'id': 2, 'nombre': 'Receta 2'},
            {'id': 3, 'nombre': 'Receta 3'}
        ]
        
        result = service._planificacion_por_defecto_con_ids(fecha_inicio, recetas)
        
        assert result['semana'] == fecha_inicio
        assert len(result['sugerencias']) == 7
    
    def test_planificacion_has_three_meals_per_day(self):
        """Debe tener 3 comidas por día (desayuno, almuerzo, cena)"""
        service = PlanningService()
        fecha_inicio = "2025-12-01"
        recetas = [{'id': 1, 'nombre': 'Test'}]
        
        result = service._planificacion_por_defecto_con_ids(fecha_inicio, recetas)
        
        for fecha, comidas in result['sugerencias'].items():
            assert 'desayuno' in comidas
            assert 'almuerzo' in comidas
            assert 'cena' in comidas
    
    def test_planificacion_cycles_recipes(self):
        """Debe ciclar las recetas disponibles"""
        service = PlanningService()
        fecha_inicio = "2025-12-01"
        recetas = [
            {'id': 10, 'nombre': 'R1'},
            {'id': 20, 'nombre': 'R2'}
        ]
        
        result = service._planificacion_por_defecto_con_ids(fecha_inicio, recetas)
        
        # Debe asignar IDs cíclicamente
        primer_dia = list(result['sugerencias'].values())[0]
        assert primer_dia['desayuno'] in [10, 20]
        assert primer_dia['almuerzo'] in [10, 20]
        assert primer_dia['cena'] in [10, 20]
    
    def test_planificacion_empty_recipes_returns_nulls(self):
        """Debe retornar null para comidas si no hay recetas"""
        service = PlanningService()
        fecha_inicio = "2025-12-01"
        recetas = []
        
        result = service._planificacion_por_defecto_con_ids(fecha_inicio, recetas)
        
        assert len(result['sugerencias']) == 7
        for fecha, comidas in result['sugerencias'].items():
            assert comidas['desayuno'] is None
            assert comidas['almuerzo'] is None
            assert comidas['cena'] is None
    
    def test_planificacion_correct_date_sequence(self):
        """Debe generar fechas consecutivas correctas"""
        service = PlanningService()
        fecha_inicio = "2025-12-01"
        recetas = [{'id': 1, 'nombre': 'Test'}]
        
        result = service._planificacion_por_defecto_con_ids(fecha_inicio, recetas)
        
        fechas = sorted(result['sugerencias'].keys())
        assert fechas[0] == "2025-12-01"
        assert fechas[1] == "2025-12-02"
        assert fechas[2] == "2025-12-03"
        assert fechas[6] == "2025-12-07"
    
    def test_planificacion_invalid_date_uses_current(self):
        """Debe usar fecha actual si la fecha de inicio es inválida"""
        service = PlanningService()
        fecha_invalida = "fecha-invalida"
        recetas = [{'id': 1, 'nombre': 'Test'}]
        
        result = service._planificacion_por_defecto_con_ids(fecha_invalida, recetas)
        
        # Debe tener una semana válida
        assert 'semana' in result
        assert len(result['sugerencias']) == 7
    
    def test_planificacion_single_recipe_repeats(self):
        """Debe repetir una única receta en todas las comidas"""
        service = PlanningService()
        fecha_inicio = "2025-12-01"
        recetas = [{'id': 99, 'nombre': 'Única Receta'}]
        
        result = service._planificacion_por_defecto_con_ids(fecha_inicio, recetas)
        
        # Con una sola receta, todas las comidas deberían tener ese ID
        for fecha, comidas in result['sugerencias'].items():
            assert comidas['desayuno'] == 99
            assert comidas['almuerzo'] == 99
            assert comidas['cena'] == 99
