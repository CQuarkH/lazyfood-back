"""
Script de prueba para el sistema de recuperación de contraseña
Ejecutar: python test_password_recovery.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_recuperar_password():
    print_section("TEST 1: Solicitar Recuperación de Contraseña")
    
    # Email de prueba (debe existir en tu base de datos)
    email = input("Ingresa el email del usuario para recuperar contraseña: ")
    
    url = f"{BASE_URL}/v1/usuarios/recuperar-password"
    payload = {
        "email": email
    }
    
    print(f"\n📤 Enviando solicitud a: {url}")
    print(f"📧 Email: {email}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\n📥 Status Code: {response.status_code}")
        print(f"📄 Response:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            print("\n✅ Solicitud exitosa!")
            print("📧 Revisa tu email o los logs del servidor para obtener el token")
            return True
        else:
            print("\n❌ Error en la solicitud")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def test_cambiar_password():
    print_section("TEST 2: Cambiar Contraseña con Token")
    
    token = input("\nIngresa el token de recuperación: ")
    new_password = input("Ingresa la nueva contraseña (mínimo 8 caracteres): ")
    
    url = f"{BASE_URL}/v1/usuarios/cambiar-password"
    payload = {
        "token": token,
        "new_password": new_password
    }
    
    print(f"\n📤 Enviando solicitud a: {url}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\n📥 Status Code: {response.status_code}")
        print(f"📄 Response:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            print("\n✅ Contraseña cambiada exitosamente!")
            return True
        else:
            print("\n❌ Error al cambiar contraseña")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def test_pagina_reset():
    print_section("TEST 3: Página de Reset de Contraseña")
    
    token = input("\nIngresa un token de prueba (o presiona Enter para usar uno de ejemplo): ")
    if not token:
        token = "ejemplo_token_123"
    
    url = f"{BASE_URL}/reset-password?token={token}"
    
    print(f"\n🌐 Abre esta URL en tu navegador:")
    print(f"   {url}")
    print("\n💡 Tip: La página te permitirá cambiar la contraseña si el token es válido")

def test_validaciones():
    print_section("TEST 4: Validaciones")
    
    test_cases = [
        {
            "name": "Email vacío",
            "payload": {"email": ""},
            "expected": 400
        },
        {
            "name": "Email inválido",
            "payload": {"email": "no_es_un_email"},
            "expected": 400
        },
        {
            "name": "Contraseña corta",
            "endpoint": "cambiar-password",
            "payload": {"token": "test", "new_password": "123"},
            "expected": 400
        },
        {
            "name": "Token vacío",
            "endpoint": "cambiar-password",
            "payload": {"token": "", "new_password": "Password123"},
            "expected": 400
        }
    ]
    
    for test in test_cases:
        print(f"\n🧪 Probando: {test['name']}")
        endpoint = test.get('endpoint', 'recuperar-password')
        url = f"{BASE_URL}/v1/usuarios/{endpoint}"
        
        try:
            response = requests.post(url, json=test['payload'])
            status = response.status_code
            
            if status == test['expected']:
                print(f"   ✅ Pasó - Status: {status}")
            else:
                print(f"   ❌ Falló - Esperado: {test['expected']}, Obtenido: {status}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def main():
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║     TEST DE RECUPERACIÓN DE CONTRASEÑA - LAZYFOOD        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    while True:
        print("\n📋 MENÚ DE PRUEBAS:")
        print("   1. Solicitar recuperación de contraseña")
        print("   2. Cambiar contraseña con token")
        print("   3. Ver página de reset en navegador")
        print("   4. Probar validaciones")
        print("   5. Ejecutar todos los tests")
        print("   0. Salir")
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            test_recuperar_password()
        elif opcion == "2":
            test_cambiar_password()
        elif opcion == "3":
            test_pagina_reset()
        elif opcion == "4":
            test_validaciones()
        elif opcion == "5":
            test_recuperar_password()
            time.sleep(1)
            continuar = input("\n¿Continuar con el cambio de contraseña? (s/n): ")
            if continuar.lower() == 's':
                test_cambiar_password()
            test_validaciones()
        elif opcion == "0":
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("\n❌ Opción inválida")
        
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
