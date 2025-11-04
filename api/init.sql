-- init.sql (actualizado)
-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla de usuarios
CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    pais VARCHAR(50),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nivel_cocina INTEGER DEFAULT 1,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de preferencias
CREATE TABLE preferencia (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    dieta VARCHAR(50),
    alergias JSONB,
    gustos JSONB,
    UNIQUE(usuario_id)
);

-- Tabla de ingredientes
CREATE TABLE ingrediente (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    categoria VARCHAR(50),
    unidad VARCHAR(20),
    emoji VARCHAR(8)  -- emoji representativo (ej: "🍅")
);

-- Tabla de inventario
CREATE TABLE inventario (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    ingrediente_id INTEGER NOT NULL REFERENCES ingrediente(id),
    cantidad DECIMAL(10,2),
    confianza DECIMAL(3,2) DEFAULT 1.0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bounding_box JSONB, -- bounding box normalizada {x,y,width,height}
    UNIQUE(usuario_id, ingrediente_id)
);

-- Tabla de recetas
CREATE TABLE receta (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    tiempo_preparacion INTEGER,
    calorias INTEGER,
    nivel_dificultad INTEGER DEFAULT 1,
    emoji VARCHAR(8) -- emoji representativo de la receta
);

-- Tabla de pasos de receta
CREATE TABLE paso_receta (
    id SERIAL PRIMARY KEY,
    receta_id INTEGER NOT NULL REFERENCES receta(id) ON DELETE CASCADE,
    numero_paso INTEGER NOT NULL,
    instruccion TEXT NOT NULL,
    temporizador_segundos INTEGER,
    UNIQUE(receta_id, numero_paso)
);

-- Tabla de sugerencias de recetas
CREATE TABLE sugerencia_receta (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    receta_id INTEGER NOT NULL REFERENCES receta(id) ON DELETE CASCADE,
    porcentaje_coincidencia DECIMAL(5,2),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de planificador
CREATE TABLE planificador (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    tipo_comida VARCHAR(20) NOT NULL, -- 'desayuno', 'almuerzo', 'cena'
    receta_id INTEGER REFERENCES receta(id),
    es_sugerida BOOLEAN DEFAULT FALSE,
    UNIQUE(usuario_id, fecha, tipo_comida)
);

-- Tabla de tokens (para futura autenticación)
CREATE TABLE token (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    jwt TEXT NOT NULL,
    fecha_expiracion TIMESTAMP NOT NULL
);

-- =============================================================================
-- DATOS DE PRUEBA (con emojis)
-- =============================================================================

-- Insertar usuarios de ejemplo
INSERT INTO usuario (nombre, correo, password, pais, nivel_cocina) VALUES
('Carlos Pérez', 'carlos@ejemplo.com', 'password123', 'Chile', 2),
('María González', 'maria@ejemplo.com', 'password123', 'Argentina', 1),
('Ana Silva', 'ana@ejemplo.com', 'password123', 'Chile', 3);

-- Insertar preferencias de ejemplo
INSERT INTO preferencia (usuario_id, dieta, alergias, gustos) VALUES
(1, 'vegano', '["nueces", "mariscos"]', '["pasta", "ensaladas", "frutas"]'),
(2, 'vegetariano', '["lactosa"]', '["queso", "pan", "verduras"]'),
(3, 'omnivoro', '[]', '["carne", "pescado", "legumbres"]');

-- Insertar ingredientes base con emoji
INSERT INTO ingrediente (nombre, categoria, unidad, emoji) VALUES
('Tomate', 'verdura', 'unidades', '🍅'),
('Cebolla', 'verdura', 'unidades', '🧅'),
('Ajo', 'verdura', 'dientes', '🧄'),
('Pasta', 'granos', 'gramos', '🍝'),
('Arroz', 'granos', 'gramos', '🍚'),
('Pollo', 'proteina', 'gramos', '🍗'),
('Huevos', 'proteina', 'unidades', '🥚'),
('Leche', 'lácteo', 'ml', '🥛'),
('Queso', 'lácteo', 'gramos', '🧀'),
('Aceite de Oliva', 'condimento', 'ml', '🫗'),
('Sal', 'condimento', 'gramos', '🧂'),
('Pimienta', 'condimento', 'gramos', '🧂'),
('Pan', 'granos', 'rebanadas', '🍞'),
('Mantequilla', 'lácteo', 'gramos', '🧈'),
('Jamón', 'proteina', 'gramos', '🍖'),
('Manzana', 'fruta', 'unidades', '🍎'),
('Plátano', 'fruta', 'unidades', '🍌'),
('Zanahoria', 'verdura', 'unidades', '🥕'),
('Papa', 'verdura', 'unidades', '🥔'),
('Brócoli', 'verdura', 'gramos', '🥦');

-- Insertar recetas de ejemplo (emoji en lugar de imagen_url)
INSERT INTO receta (nombre, tiempo_preparacion, calorias, nivel_dificultad, emoji) VALUES
('Ensalada de Tomate', 10, 150, 1, '🥗'),
('Pasta con Tomate', 20, 320, 1, '🍝'),
('Huevos Revueltos', 5, 200, 1, '🍳'),
('Sándwich de Jamón y Queso', 5, 350, 1, '🥪'),
('Arroz Blanco', 15, 200, 1, '🍚'),
('Brócoli al Vapor', 10, 80, 1, '🥦');

-- Insertar pasos para las recetas
INSERT INTO paso_receta (receta_id, numero_paso, instruccion, temporizador_segundos) VALUES
-- Pasta con Tomate (id 2)
(2, 1, 'Hervir agua con sal en una olla grande', 300),
(2, 2, 'Cocinar la pasta según las instrucciones del paquete', 600),
(2, 3, 'Picar tomates y ajo finamente', NULL),
(2, 4, 'Saltear tomate y ajo en aceite de oliva', 180),
(2, 5, 'Mezclar la pasta con la salsa y servir', NULL),
-- Huevos Revueltos (id 3)
(3, 1, 'Batir los huevos en un bol', NULL),
(3, 2, 'Calentar mantequilla en una sartén', 60),
(3, 3, 'Verter los huevos y cocinar revolviendo constantemente', 180),
(3, 4, 'Servir caliente', NULL),
-- Sándwich de Jamón y Queso (id 4)
(4, 1, 'Tomar dos rebanadas de pan', NULL),
(4, 2, 'Colocar jamón y queso entre las rebanadas', NULL),
(4, 3, 'Tostar en sándwichera por 3 minutos', 180),
(4, 4, 'Servir caliente', NULL);

-- Insertar inventario inicial para el usuario 1 (bounding_box NULL posible)
INSERT INTO inventario (usuario_id, ingrediente_id, cantidad, confianza) VALUES
(1, 1, 3, 0.95),  -- Tomate
(1, 4, 500, 0.90), -- Pasta
(1, 10, 100, 0.85), -- Aceite de Oliva
(1, 11, 50, 0.80), -- Sal
(2, 7, 12, 0.95),  -- Huevos (usuario 2)
(2, 13, 8, 0.90), -- Pan (usuario 2)
(2, 14, 100, 0.85); -- Mantequilla (usuario 2)

-- Crear índices para mejorar performance
CREATE INDEX idx_inventario_usuario ON inventario(usuario_id);
CREATE INDEX idx_planificador_usuario_fecha ON planificador(usuario_id, fecha);
CREATE INDEX idx_sugerencia_usuario_fecha ON sugerencia_receta(usuario_id, fecha);
CREATE INDEX idx_usuario_correo ON usuario(correo);
