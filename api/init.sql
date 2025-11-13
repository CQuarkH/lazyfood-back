-- init.sql (actualizado)
-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla de usuarios
CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(20) DEFAULT 'user' NOT NULL,
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


-- Crear índices para mejorar performance
CREATE INDEX idx_inventario_usuario ON inventario(usuario_id);
CREATE INDEX idx_planificador_usuario_fecha ON planificador(usuario_id, fecha);
CREATE INDEX idx_sugerencia_usuario_fecha ON sugerencia_receta(usuario_id, fecha);
CREATE INDEX idx_usuario_correo ON usuario(correo);
