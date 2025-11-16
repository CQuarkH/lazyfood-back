"""
Manejador centralizado de respuestas y errores HTTP
Proporciona funciones para generar respuestas consistentes en toda la API
"""
from flask import jsonify
from typing import Any, Dict, Optional, Union, List


class ResponseHandler:
    """Clase para manejar respuestas HTTP de forma consistente"""
    
    @staticmethod
    def success(data: Any = None, message: str = None, status_code: int = 200) -> tuple:
        """
        Genera una respuesta exitosa
        
        Args:
            data: Datos a devolver en la respuesta
            message: Mensaje opcional
            status_code: Código HTTP (por defecto 200)
            
        Returns:
            tuple: (response, status_code)
        """
        response = {}
        
        if message:
            response['mensaje'] = message
            
        if data is not None:
            if isinstance(data, dict):
                response.update(data)
            else:
                response['data'] = data
                
        return jsonify(response), status_code
    
    @staticmethod
    def created(data: Any = None, message: str = "Recurso creado exitosamente") -> tuple:
        """
        Genera una respuesta de recurso creado (201)
        
        Args:
            data: Datos del recurso creado
            message: Mensaje de éxito
            
        Returns:
            tuple: (response, 201)
        """
        return ResponseHandler.success(data, message, 201)
    
    @staticmethod
    def error(message: str, status_code: int = 400, details: Any = None) -> tuple:
        """
        Genera una respuesta de error
        
        Args:
            message: Mensaje de error
            status_code: Código HTTP de error
            details: Detalles adicionales del error (opcional)
            
        Returns:
            tuple: (response, status_code)
        """
        response = {'error': message}
        
        if details:
            response['detalle'] = details
            
        return jsonify(response), status_code
    
    @staticmethod
    def bad_request(message: str = "Datos inválidos") -> tuple:
        """Respuesta de solicitud incorrecta (400)"""
        return ResponseHandler.error(message, 400)
    
    @staticmethod
    def unauthorized(message: str = "No autorizado") -> tuple:
        """Respuesta de no autorizado (401)"""
        return ResponseHandler.error(message, 401)
    
    @staticmethod
    def forbidden(message: str = "Acceso denegado") -> tuple:
        """Respuesta de acceso prohibido (403)"""
        return ResponseHandler.error(message, 403)
    
    @staticmethod
    def not_found(message: str = "Recurso no encontrado") -> tuple:
        """Respuesta de recurso no encontrado (404)"""
        return ResponseHandler.error(message, 404)
    
    @staticmethod
    def conflict(message: str = "Conflicto con el estado actual") -> tuple:
        """Respuesta de conflicto (409)"""
        return ResponseHandler.error(message, 409)
    
    @staticmethod
    def internal_error(message: str = "Ocurrió un error interno. Intente más tarde.") -> tuple:
        """Respuesta de error interno del servidor (500)"""
        return ResponseHandler.error(message, 500)


class ErrorMessages:
    """Mensajes de error estandarizados"""
    
    # Errores de validación (400)
    INVALID_DATA = "Datos inválidos"
    MISSING_FIELDS = "Faltan campos requeridos"
    INVALID_FORMAT = "Formato de datos inválido"
    INVALID_EMAIL = "El formato del email es inválido"
    INVALID_PASSWORD = "La contraseña no cumple con los requisitos"
    
    # Errores de autenticación (401)
    INVALID_CREDENTIALS = "Credenciales inválidas"
    TOKEN_MISSING = "Token no proporcionado"
    TOKEN_INVALID = "Token inválido o expirado"
    TOKEN_EXPIRED = "Token expirado"
    INACTIVE_ACCOUNT = "Cuenta inactiva"
    
    # Errores de autorización (403)
    FORBIDDEN = "No tienes permisos para realizar esta acción"
    ONLY_OWN_ACCOUNT = "Solo puedes modificar tu propia cuenta"
    
    # Errores de recursos (404)
    USER_NOT_FOUND = "Usuario no encontrado"
    RESOURCE_NOT_FOUND = "Recurso no encontrado"
    PREFERENCES_NOT_FOUND = "Preferencias no encontradas"
    
    # Errores de conflicto (409)
    USER_ALREADY_EXISTS = "Usuario ya registrado."
    EMAIL_ALREADY_EXISTS = "El email ya está registrado"
    DUPLICATE_RESOURCE = "El recurso ya existe"
    
    # Errores del servidor (500)
    INTERNAL_ERROR = "Ocurrió un error interno. Intente más tarde."
    DATABASE_ERROR = "Error en la base de datos"
    UNEXPECTED_ERROR = "Error inesperado del servidor"


class SuccessMessages:
    """Mensajes de éxito estandarizados"""
    
    # Usuarios
    USER_CREATED = "Usuario creado correctamente"
    USER_UPDATED = "Usuario actualizado exitosamente"
    USER_DELETED = "Usuario eliminado exitosamente"
    
    # Preferencias
    PREFERENCES_UPDATED = "Preferencias actualizadas exitosamente"
    PREFERENCES_CREATED = "Preferencias creadas exitosamente"
    
    # Autenticación
    LOGIN_SUCCESS = "Inicio de sesión exitoso"
    LOGOUT_SUCCESS = "Cierre de sesión exitoso"
    TOKEN_REFRESHED = "Token renovado exitosamente"
    
    # Contraseña
    PASSWORD_RECOVERY_SENT = "Enlace de recuperación generado exitosamente"
    PASSWORD_UPDATED = "Contraseña actualizada exitosamente"
    
    # General
    OPERATION_SUCCESS = "Operación realizada exitosamente"


# Instancia global para facilitar el uso
response = ResponseHandler()
errors = ErrorMessages()
success = SuccessMessages()
