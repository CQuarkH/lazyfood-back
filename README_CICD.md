# Guía de Configuración CI/CD - LazyFood

Esta guía te llevará paso a paso para configurar el pipeline de CI/CD para el proyecto LazyFood usando GitHub Actions y GitHub Container Registry.

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Paso 1: Configurar Secrets en GitHub](#paso-1-configurar-secrets-en-github)
3. [Paso 2: Crear Personal Access Token para GHCR](#paso-2-crear-personal-access-token-para-ghcr)
4. [Paso 3: Preparar el Servidor VPS](#paso-3-preparar-el-servidor-vps)
5. [Paso 4: Crear archivo .env de Producción](#paso-4-crear-archivo-env-de-producción)
6. [Paso 5: Probar el Pipeline](#paso-5-probar-el-pipeline)
7. [Troubleshooting](#troubleshooting)

---

## Requisitos Previos

Antes de comenzar, asegúrate de tener:

- ✅ Cuenta de GitHub con el repositorio `CQuarkH/lazyfood-back`
- ✅ Un servidor VPS (Ubuntu/Debian recomendado) con acceso SSH
- ✅ Docker y Docker Compose instalados en el VPS
- ✅ Clave SSH para acceder al VPS
- ✅ API Key de Google AI (Gemini)

---

## Paso 1: Configurar Secrets en GitHub

Los secrets almacenan información sensible como contraseñas y claves SSH de forma segura.

### 1.1. Acceder a la configuración de Secrets

1. Ve a tu repositorio: `https://github.com/CQuarkH/lazyfood-back`
2. Click en **Settings** (Configuración)
3. En el menú lateral izquierdo, click en **Secrets and variables** → **Actions**
4. Click en el botón verde **New repository secret**

### 1.2. Crear los Secrets necesarios

Deberás crear **4 secrets**. Para cada uno:

#### Secret 1: `SSH_HOST`

- **Name:** `SSH_HOST`
- **Value:** La IP pública de tu servidor VPS (ejemplo: `123.45.67.89`)

#### Secret 2: `SSH_USER`

- **Name:** `SSH_USER`
- **Value:** El usuario SSH (ejemplo: `root` o `ubuntu`)

#### Secret 3: `SSH_KEY`

- **Name:** `SSH_KEY`
- **Value:** Tu clave privada SSH **completa**

**Cómo obtener la clave SSH en Windows:**

```powershell
# Opción 1: Copiar al portapapeles
Get-Content ~\.ssh\id_rsa | clip

# Opción 2: Ver en pantalla
Get-Content ~\.ssh\id_rsa
```

**Cómo obtener la clave SSH en Linux/Mac:**

```bash
# Opción 1: Copiar al portapapeles (Mac)
cat ~/.ssh/id_rsa | pbcopy

# Opción 2: Copiar al portapapeles (Linux con xclip)
cat ~/.ssh/id_rsa | xclip -selection clipboard

# Opción 3: Ver en pantalla
cat ~/.ssh/id_rsa
```

> [!IMPORTANT]
> Copia TODO el contenido, desde `-----BEGIN OPENSSH PRIVATE KEY-----` hasta `-----END OPENSSH PRIVATE KEY-----` (incluidos)

#### Secret 4: `ENV_FILE`

- **Name:** `ENV_FILE`
- **Value:** El contenido completo de tu archivo `.env` de producción

**Ejemplo de contenido:**

```env
# Base de datos
DATABASE_URL=postgresql://lazyfood_user:lazyfood_pass@db:5432/lazyfood_db

# API Keys
GOOGLE_AI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_MODEL=models/gemini-2.5-flash
GEMINI_CV_MODEL=gemini-2.5-flash

# Flask
SECRET_KEY=tu_secret_key_super_seguro_de_produccion_aqui
DEBUG=False
PORT=5000

# JWT
JWT_SECRET_KEY=tu_clave_jwt_diferente_a_secret_key_aqui
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# CORS (dominios permitidos, separados por coma)
CORS_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com

# Rate Limiting
RATELIMIT_ENABLED=True
RATELIMIT_DEFAULT=100 per hour
RATELIMIT_STORAGE_URL=memory://

# Email (Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_app_password_de_gmail
MAIL_DEFAULT_SENDER=noreply@lazyfood.com
```

> [!WARNING]
> **NO incluyas** `POSTGRES_USER`, `POSTGRES_PASSWORD` ni `POSTGRES_DB` en este archivo. El workflow los agregará automáticamente.

### 1.3. Verificar que todos los secrets estén creados

Deberías ver 4 secrets en la lista:
- `SSH_HOST`
- `SSH_USER`
- `SSH_KEY`
- `ENV_FILE`

---

## Paso 2: Crear Personal Access Token para GHCR

El servidor VPS necesita autenticarse con GitHub Container Registry para descargar las imágenes Docker.

### 2.1. Crear el Token

1. Ve a: `https://github.com/settings/tokens`
2. Click en **Generate new token** → **Generate new token (classic)**
3. Dale un nombre descriptivo (ejemplo: `VPS LazyFood - GHCR`)
4. Marca **solo** el permiso: `read:packages`
5. Click en **Generate token** (al final de la página)
6. **¡COPIA EL TOKEN INMEDIATAMENTE!** (Solo se muestra una vez)

Guarda el token en un lugar seguro, lo necesitarás en el siguiente paso.

---

## Paso 3: Preparar el Servidor VPS

### 3.1. Verificar instalación de Docker

Conéctate a tu VPS por SSH:

```bash
ssh tu_usuario@tu_servidor
```

Verifica que Docker y Docker Compose estén instalados:

```bash
docker --version
docker compose version
```

**Si no están instalados**, ejecuta:

```bash
# Actualizar paquetes
sudo apt update

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar tu usuario al grupo docker (para no usar sudo)
sudo usermod -aG docker $USER

# Aplicar cambios de grupo (o reinicia la sesión)
newgrp docker

# Verificar instalación
docker --version
docker compose version
```

### 3.2. Crear directorio de trabajo

```bash
# Crear directorio para la aplicación
sudo mkdir -p /opt/lazyfood

# Dar permisos a tu usuario
sudo chown -R $USER:$USER /opt/lazyfood

# Navegar al directorio
cd /opt/lazyfood
```

### 3.3. Autenticar con GitHub Container Registry

Usa el Personal Access Token que creaste en el Paso 2:

```bash
# Sustituye TU_TOKEN con el token que copiaste
# Sustituye CQuarkH con tu usuario de GitHub si es diferente
echo "TU_TOKEN" | docker login ghcr.io -u CQuarkH --password-stdin
```

Deberías ver el mensaje: `Login Succeeded`

### 3.4. Verificar conectividad del servidor

Asegúrate de que el servidor pueda acceder a GitHub:

```bash
curl -I https://github.com
curl -I https://raw.githubusercontent.com
```

Ambos deberían devolver `HTTP/2 200` o similar.

---

## Paso 4: Crear archivo .env de Producción

> [!NOTE]
> **Este paso es OPCIONAL.** El workflow de GitHub Actions creará automáticamente el archivo `.env` en el servidor. Sin embargo, puedes crearlo manualmente para verificar que todo funcione.

Si quieres crear el `.env` manualmente en el VPS:

```bash
cd /opt/lazyfood

# Crear el archivo .env
nano .env
```

Pega el mismo contenido que usaste en el secret `ENV_FILE` de GitHub.

Guarda y cierra (Ctrl+X, luego Y, luego Enter).

---

## Paso 5: Probar el Pipeline

### 5.1. Hacer commit y push de los archivos

En tu máquina local, en la rama `ci-cd`:

```bash
cd c:\Users\Ainsi\Desktop\proyectos\lazyfood-back

# Verificar los archivos creados
git status

# Agregar los archivos
git add docker-compose.prod.yml .github/workflows/cicd.yml

# Hacer commit
git commit -m "feat: agregar configuración de CI/CD pipeline"

# Push a la rama ci-cd
git push origin ci-cd
```

### 5.2. Verificar que los tests se ejecuten

1. Ve a tu repositorio en GitHub
2. Click en la pestaña **Actions**
3. Deberías ver un workflow en ejecución llamado "CI/CD Pipeline - LazyFood"
4. Click en él para ver los detalles
5. Verifica que el job `test` se ejecute correctamente

> [!NOTE]
> En esta etapa, **solo se ejecutará el job `test`** (los tests unitarios). Los jobs `build-and-push` y `deploy` NO se ejecutarán porque solo corren cuando hay push a la rama `main`.

### 5.3. Crear Pull Request

Si los tests pasan:

1. Ve a `https://github.com/CQuarkH/lazyfood-back/pulls`
2. Click en **New Pull Request**
3. Selecciona `base: main` ← `compare: ci-cd`
4. Click en **Create Pull Request**
5. Revisa los cambios
6. Click en **Create Pull Request**

### 5.4. Merge a main (Despliegue Automático)

> [!WARNING]
> **ANTES DE HACER MERGE**, asegúrate de que:
> - ✅ Todos los secrets estén configurados en GitHub
> - ✅ El VPS esté preparado (directorio creado, Docker instalado)
> - ✅ El VPS esté autenticado con GHCR (`docker login ghcr.io`)
> - ✅ Los tests hayan pasado en el PR

Una vez verificado todo:

1. En el Pull Request, click en **Merge pull request**
2. Click en **Confirm merge**
3. Ve a la pestaña **Actions**
4. Verás el pipeline ejecutándose con los **3 jobs**:
   - `test` (Tests Unitarios) ✅
   - `build-and-push` (Construir y Publicar Imágenes) 🏗️
   - `deploy` (Desplegar en VPS) 🚀

### 5.5. Verificar el despliegue

El pipeline tardará aproximadamente 5-10 minutos en completarse.

Una vez que termine:

```bash
# Conectar al VPS
ssh tu_usuario@tu_servidor

# Navegar al directorio
cd /opt/lazyfood

# Ver los contenedores en ejecución
docker compose -f docker-compose.prod.yml ps

# Ver logs de todos los servicios
docker compose -f docker-compose.prod.yml logs

# Ver logs de un servicio específico
docker compose -f docker-compose.prod.yml logs backend -f
docker compose -f docker-compose.prod.yml logs ml-service -f
docker compose -f docker-compose.prod.yml logs db -f
```

### 5.6. Probar la API

```bash
# Desde el VPS
curl http://localhost:5000/

# Probar el health check del ML service
curl http://localhost:8001/api/v1/health
```

Si todo funciona, deberías recibir respuestas JSON.

---

## Troubleshooting

### ❌ Error: "Permission denied (publickey)"

**Causa:** La clave SSH en el secret `SSH_KEY` no es válida o no tiene permisos en el servidor.

**Solución:**

1. Verifica que copiaste la clave SSH **completa** (desde `-----BEGIN` hasta `-----END`)
2. Asegúrate de que la clave pública (`id_rsa.pub`) esté en el servidor:
   ```bash
   ssh tu_usuario@tu_servidor
   cat ~/.ssh/authorized_keys
   ```
3. Si no está, agrégala:
   ```bash
   # En tu máquina local
   cat ~/.ssh/id_rsa.pub
   # Copia el contenido
   
   # En el VPS
   echo "CONTENIDO_DE_TU_CLAVE_PUBLICA" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

### ❌ Error: "unauthorized: unauthenticated" al hacer pull

**Causa:** El VPS no está autenticado con GitHub Container Registry.

**Solución:**

```bash
# En el VPS
echo "TU_PERSONAL_ACCESS_TOKEN" | docker login ghcr.io -u CQuarkH --password-stdin
```

### ❌ Error: "Cannot connect to Docker daemon"

**Causa:** Docker no está corriendo en el VPS.

**Solución:**

```bash
# Verificar estado de Docker
sudo systemctl status docker

# Si no está corriendo, iniciarlo
sudo systemctl start docker

# Habilitar para que inicie automáticamente
sudo systemctl enable docker
```

### ❌ Los tests fallan en GitHub Actions

**Causa:** Algún test unitario está fallando.

**Solución:**

1. Ejecuta los tests localmente:
   ```bash
   docker build -t lazyfood-test -f Dockerfile.test .
   docker run --rm lazyfood-test
   ```
2. Revisa los errores y corrígelos
3. Haz commit y push de nuevo

### ❌ Error: "No space left on device"

**Causa:** El VPS se quedó sin espacio en disco.

**Solución:**

```bash
# En el VPS, limpiar imágenes antiguas
docker system prune -a

# Ver espacio disponible
df -h
```

### ❌ La aplicación no responde después del deploy

**Causa:** Los contenedores pueden no estar iniciando correctamente.

**Solución:**

```bash
# Ver logs de todos los servicios
cd /opt/lazyfood
docker compose -f docker-compose.prod.yml logs

# Ver estado de los contenedores
docker compose -f docker-compose.prod.yml ps

# Reiniciar los servicios
docker compose -f docker-compose.prod.yml restart

# Si persiste, detener y volver a levantar
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

---

## 🎉 ¡Pipeline Configurado!

Una vez que todo esté funcionando, cada vez que hagas push a la rama `main`:

1. ✅ Se ejecutarán los tests automáticamente
2. ✅ Si los tests pasan, se construirán las imágenes Docker
3. ✅ Las imágenes se publicarán en GitHub Container Registry
4. ✅ Se desplegará automáticamente en tu servidor VPS

**¡Ya tienes CI/CD funcionando!** 🚀

---

## Recursos Adicionales

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
