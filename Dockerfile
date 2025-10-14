# 1. Base Image
FROM python:3.11-slim

# 2. Set Working Directory
WORKDIR /app

# 3. Copy and Install Dependencies
# Copiamos solo el requirements.txt primero para aprovechar el cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Files
# Copiamos el resto del proyecto. El .dockerignore evitará que entre basura.
COPY . .

# 5. Configuration (Si app.py es el punto de entrada principal)
# Asegúrate de que tu Flask app instance esté definida en app.py como 'app'
# Por ejemplo, en app.py deberías tener: app = Flask(__name__)
# Y aquí usamos Gunicorn, el servidor WSGI de producción:
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

# 6. Expose Port
EXPOSE 5000