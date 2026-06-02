Proyecto: CyberBot (Chatbot experto en ciberseguridad)
===============================================

Descripción
-----------
CyberBot es un chatbot de diagnóstico conversacional para incidentes de
ciberseguridad. Implementa una base de conocimiento basada en JSON (carpeta
`data/`) y un motor de inferencia híbrido (similitud TF-IDF + CountVectorizer
y reglas por síntomas) en `src/inference_engine.py`.

Contenido relevante
-------------------
- `main.py` : punto de entrada para lanzar la GUI.
- `evaluate.py` : script de evaluación (métricas y gráficas).
- `data/` : datasets JSON usados como base de conocimiento.
- `src/` : código fuente del bot (NLU, inference engine, GUI, session, etc.).

Instalación de dependencias
---------------------------
Este proyecto usa un conjunto de librerías instalables con pip.
Para preparar el entorno, sitúate en la carpeta `Chatbot` y ejecuta:

python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Esto instalará todas las librerías necesarias para ejecutar la interfaz gráfica,
la evaluación y el procesamiento de lenguaje.

Dependencias incluidas en `requirements.txt`
------------------------------------------
- numpy
- nltk
- scikit-learn
- matplotlib
- seaborn

Dependencia opcional
---------------------
Si quieres usar el módulo `src/external_qa.py`, instala también:

python -m pip install apify-client

Preparación de NLTK
------------------
Al primer uso, NLTK descargará recursos puntuales. Si no lo hace automáticamente:

python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

Ejecución
---------
1) Ejecutar la GUI (modo interactivo):

   python main.py

   - Abre la interfaz gráfica y permite interactuar con el chatbot.

2) Ejecutar la evaluación y generar gráficos:

   python evaluate.py

   - Genera métricas y tres imágenes: `prf_metrics.png`,
     `confusion_matrix.png` y `support.png` en el directorio actual.

Configuración opcional: `external_qa.py`
------------------------------------
El módulo `src/external_qa.py` usa la API de Apify. Si quieres usarlo,
establece la variable de entorno `APIFY_TOKEN`. El código verifica si el token
está presente antes de hacer llamadas remotas; si no está, el módulo queda
desactivado.