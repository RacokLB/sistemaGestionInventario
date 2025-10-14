# 1. Base Image
FROM python:3.11-slim

# Establece variables de entorno estándar de Python
ENV PYTHONUNBUFFERED 1
# Establece el puerto de escucha. Render inyecta la variable PORT, 
# si no está disponible, usamos 8080 como fallback.
ENV PORT 8080

# --- NUEVAS VARIABLES DE ENTORNO PARA LA DB (Añadidas) ---
# Estas variables son las que tu config.py está leyendo (os.environ.get('MYSQL_USER'))
# Render te pedirá que definas estas mismas variables en su interfaz de despliegue.
ENV MYSQL_USER=root
ENV MYSQL_PASSWORD=
ENV MYSQL_HOST=localhost
ENV MYSQL_PORT=3306
ENV MYSQL_DATABASE=roberth
# --------------------------------------------------------

# 2. Set Working Directory
WORKDIR /app

# 3. Copy and Install Dependencies
# Copiamos solo el requirements.txt primero para aprovechar el cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Files
# Copiamos el resto del proyecto. El .dockerignore evitará que entre basura.
COPY . .

# 5. Configuration: Comando de Ejecución con Gunicorn
# Usamos el comando 'CMD' para que Gunicorn use la variable de entorno PORT.
# Ejecutamos con 'sh -c' para permitir la expansión de variables.
# El formato sigue siendo 'nombre_del_archivo_flask:nombre_de_la_instancia_flask'
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} app:app"]

# 6. Expose Port
# El puerto expuesto debe ser el mismo que Gunicorn está escuchando (8080/PORT)
EXPOSE 8080
