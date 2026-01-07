
# Dashboard de Señales del Mercado Financiero Local (Bolsa de Valores de Ecuador) – Producto Mínimo Viable (MVP)

Este repositorio contiene una aplicación en Streamlit que carga datos en vivo desde Hugging Face (HF) para visualizar señales básicas del mercado financiero ecuatoriano.

## Objetivo
Publicar rápidamente un panel interactivo con Indicadores Clave de Desempeño (KPI) para monto y volumen negociado, ranking de emisores, y series temporales, usando datos publicados en Hugging Face Datasets.

## Aclaración de siglas
- Producto Mínimo Viable (MVP): versión mínima funcional del producto para validar la idea con usuarios.
- Hugging Face (HF): plataforma colaborativa para modelos y datos.
- HF Spaces (Hugging Face Spaces): servicio de alojamiento de aplicaciones web (como Streamlit) en la nube de HF.
- Interfaz de Programación de Aplicaciones (API): conjunto de funciones o endpoints para que sistemas se comuniquen.
- Indicador Clave de Desempeño (KPI): métrica utilizada para evaluar rendimiento o actividad.

## Estructura del proyecto
```text
mvp-bolsa-ec/
├─ app.py                  # App principal de Streamlit; contiene comentarios extensos explicando cada sección
├─ requirements.txt        # Dependencias necesarias para ejecutar la app
├─ .streamlit/
│  └─ config.toml          # Tema de la aplicación (colores y tipografía)
└─ .gitignore              # Archivos a ignorar en control de versiones
```

## Datos
- Fuente: Hugging Face Datasets.
- Identificador del dataset (ajustable en app.py): beta3/Historical_Data_of_Ecuador_Stock_Exchange.
- Licencia: consultar la tarjeta del dataset en HF para confirmar detalles (por ejemplo, Creative Commons Atribución-CompartirIgual 4.0 (CC BY-SA 4.0) si así lo declara el autor).
- Nota: el código intenta estandarizar nombres de columnas de forma flexible para funcionar aunque cambie la nomenclatura.

## Ejecución local
1. Crear un entorno virtual (opcional pero recomendado).
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar la aplicación:
   ```bash
   streamlit run app.py
   ```

## Publicación en Hugging Face Spaces (HF Spaces)
1. Crear un Space nuevo en HF y elegir el SDK Streamlit.
2. Subir estos archivos a tu Space o conectar con tu repositorio en GitHub.
3. Verificar que requirements.txt está en la raíz del proyecto.
4. La aplicación se construirá automáticamente. En caso de error, revisar los logs del Space.

## Cómo está organizado el código (guía)
- DATASET_ID: variable editable para apuntar al dataset de HF.
- load_data_from_hf: función cacheada que descarga y convierte la primera partición del dataset a pandas.DataFrame.
- standardize_columns: intenta renombrar columnas a un conjunto estándar (date, issuer, traded_value, traded_volume, instrument_type, exchange, price).
- Barra lateral (st.sidebar): filtros por fecha, emisor y tipo de instrumento (si existen en el dataset).
- KPI: monto negociado total, volumen total y número de registros en el filtro.
- Gráficos:
  - Serie temporal con monto (línea) y volumen (barra, en eje secundario) agregados por fecha.
  - Ranking de emisores por monto o volumen (top 20).
- Tabla de detalle y botón de descarga del CSV filtrado.
- Sección de diagnóstico para inspeccionar la estructura real de columnas.

## Checklist de escalamiento
- [ ] Agregar vista por bolsa (Bolsa de Valores de Quito, BVQ; Bolsa de Valores de Guayaquil, BVG) si existe la columna exchange.
- [ ] Incorporar clasificación por sector económico si existe una columna de sector o industria.
- [ ] Añadir alertas configurables (por ejemplo, cambios porcentuales semanales o mensuales).
- [ ] Migrar a una base de datos administrada (por ejemplo, Supabase (PostgreSQL)) si se requieren datos propios o curados.
- [ ] Contenerizar con Docker y desplegar en Google Cloud Run si aumenta el tráfico.
- [ ] Añadir una pestaña educativa con glosario de términos financieros.

## Notas finales
- Si el dataset cambia nombres de columnas, edita o amplía el mapeo en standardize_columns.
- Mantén el identificador del dataset en una sola variable para no propagar cambios por el código.
- Verifica la licencia del dataset en su tarjeta antes de uso público.
