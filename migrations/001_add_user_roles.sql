-- Migración: Agregar columna 'rol' a la tabla usuario
-- Fecha: 2024-11-06
-- Descripción: Agrega soporte para roles de usuario (admin, user)

-- Agregar columna rol si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='usuario' AND column_name='rol'
    ) THEN
        ALTER TABLE usuario ADD COLUMN rol VARCHAR(20) DEFAULT 'user' NOT NULL;
        RAISE NOTICE 'Columna rol agregada exitosamente';
    ELSE
        RAISE NOTICE 'La columna rol ya existe';
    END IF;
END $$;

-- Actualizar usuarios existentes sin rol
UPDATE usuario SET rol = 'user' WHERE rol IS NULL OR rol = '';

-- Crear un usuario administrador por defecto si no existe
INSERT INTO usuario (nombre, correo, password, rol, pais, nivel_cocina, activo)
SELECT 'Admin User', 'admin@lazyfood.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lE7ZGBvxLhzu', 'admin', 'Chile', 3, true
WHERE NOT EXISTS (
    SELECT 1 FROM usuario WHERE correo = 'admin@lazyfood.com'
);

-- Mostrar resumen
DO $$
DECLARE
    total_users INTEGER;
    admin_users INTEGER;
    regular_users INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_users FROM usuario;
    SELECT COUNT(*) INTO admin_users FROM usuario WHERE rol = 'admin';
    SELECT COUNT(*) INTO regular_users FROM usuario WHERE rol = 'user';
    
    RAISE NOTICE '';
    RAISE NOTICE '=== Resumen de Migración ===';
    RAISE NOTICE 'Total de usuarios: %', total_users;
    RAISE NOTICE 'Administradores: %', admin_users;
    RAISE NOTICE 'Usuarios regulares: %', regular_users;
    RAISE NOTICE '';
    RAISE NOTICE 'Usuario admin por defecto:';
    RAISE NOTICE 'Correo: admin@lazyfood.com';
    RAISE NOTICE 'Contraseña: Password123!';
    RAISE NOTICE '';
END $$;
