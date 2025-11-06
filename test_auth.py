#!/usr/bin/env python3
"""
Script de prueba para el sistema de autenticación de LazyFood API
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"

def print_section(title):
    """Imprime un separador con título"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_response(response):
    """Imprime la respuesta de manera formateada"""
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)

def test_login():
    """Prueba el endpoint de login"""
    print_section("TEST 1: Login como Admin")
    
    response = requests.post(
        f"{BASE_URL}/v1/auth/login",
        json={
            "correo": "admin@lazyfood.com",
            "password": "Password123!"
        }
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token'), data.get('refresh_token')
    
    return None, None

def test_get_current_user(token):
    """Prueba obtener información del usuario actual"""
    print_section("TEST 2: Obtener Usuario Actual")
    
    response = requests.get(
        f"{BASE_URL}/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print_response(response)

def test_list_users(token):
    """Prueba listar usuarios (solo admin)"""
    print_section("TEST 3: Listar Usuarios (Admin)")
    
    response = requests.get(
        f"{BASE_URL}/v1/usuarios",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print_response(response)

def test_refresh_token(refresh_token):
    """Prueba renovar el access token"""
    print_section("TEST 4: Renovar Access Token")
    
    response = requests.post(
        f"{BASE_URL}/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token')
    
    return None

def test_unauthorized_access():
    """Prueba acceso sin token"""
    print_section("TEST 5: Acceso Sin Token (debe fallar)")
    
    response = requests.get(f"{BASE_URL}/v1/usuarios")
    
    print_response(response)

def test_invalid_token():
    """Prueba con token inválido"""
    print_section("TEST 6: Token Inválido (debe fallar)")
    
    response = requests.get(
        f"{BASE_URL}/v1/auth/me",
        headers={"Authorization": "Bearer token_invalido"}
    )
    
    print_response(response)

def test_user_login():
    """Prueba login como usuario regular"""
    print_section("TEST 7: Login como Usuario Regular")
    
    response = requests.post(
        f"{BASE_URL}/v1/auth/login",
        json={
            "correo": "carlos@ejemplo.com",
            "password": "Password123!"
        }
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token')
    
    return None

def test_user_access_forbidden(user_token):
    """Prueba que un usuario regular no puede listar usuarios"""
    print_section("TEST 8: Usuario Regular Intenta Listar Usuarios (debe fallar)")
    
    response = requests.get(
        f"{BASE_URL}/v1/usuarios",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    print_response(response)

def test_register():
    """Prueba registro de nuevo usuario"""
    print_section("TEST 9: Registro de Nuevo Usuario")
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    response = requests.post(
        f"{BASE_URL}/v1/usuarios/registro",
        json={
            "nombre": "Test User",
            "correo": f"test_{timestamp}@ejemplo.com",
            "password": "Password123!"
        }
    )
    
    print_response(response)

def test_logout(access_token, refresh_token):
    """Prueba logout"""
    print_section("TEST 10: Logout")
    
    response = requests.post(
        f"{BASE_URL}/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token}
    )
    
    print_response(response)

def main():
    """Ejecuta todas las pruebas"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     PRUEBAS DE AUTENTICACIÓN Y AUTORIZACIÓN - LazyFood    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    try:
        # Test 1: Login como admin
        admin_token, admin_refresh = test_login()
        if not admin_token:
            print("\n❌ Error: No se pudo hacer login como admin")
            return
        
        # Test 2: Obtener usuario actual
        test_get_current_user(admin_token)
        
        # Test 3: Listar usuarios (admin)
        test_list_users(admin_token)
        
        # Test 4: Renovar token
        new_token = test_refresh_token(admin_refresh)
        if new_token:
            admin_token = new_token
        
        # Test 5: Acceso sin token
        test_unauthorized_access()
        
        # Test 6: Token inválido
        test_invalid_token()
        
        # Test 7: Login como usuario regular
        user_token = test_user_login()
        
        # Test 8: Usuario regular intenta listar usuarios
        if user_token:
            test_user_access_forbidden(user_token)
        
        # Test 9: Registro de nuevo usuario
        test_register()
        
        # Test 10: Logout
        test_logout(admin_token, admin_refresh)
        
        print_section("✅ Todas las pruebas completadas")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se pudo conectar al servidor.")
        print("   Asegúrate de que la API esté corriendo en http://localhost:5000")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")

if __name__ == "__main__":
    main()
