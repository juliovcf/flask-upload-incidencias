from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import pandas as pd
from castles_manager import CastlesManager  # Importar la clase de gestión de Castles

app = Flask(__name__)

# Crear una instancia de CastlesManager
castles_manager = CastlesManager()

# Ruta principal para subir el archivo de incidencias y mostrar la tabla
@app.route('/', methods=['GET', 'POST'])
def upload_file_and_show_data():
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file:
            # Procesar el archivo de incidencias
            df = pd.read_excel(file)

            # Extraer "Centro" y "Caja"
            df['Centro'] = df['Ubicación'].str.extract(r'(\d+)')
            df['Caja'] = df['CI impactado'].str.extract(r'(caj\d+)')

            # Seleccionar las columnas que queremos guardar y reordenar
            df_to_save = df[['Número', 'Centro', 'Caja', 'Breve descripción', 'Grupo de asignación', 'Fecha de creación']]

            # Convertir los NaN en cadenas vacías
            df_to_save = df_to_save.fillna('')

            # Asegurarse de que la fecha sea una cadena
            df_to_save['Fecha de creación'] = df_to_save['Fecha de creación'].astype(str)

            # Conectar a la base de datos
            conn = sqlite3.connect('incidencias.db')
            cursor = conn.cursor()

            # Crear la tabla de incidencias si no existe
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidencias (
                numero TEXT PRIMARY KEY,
                centro TEXT,
                caja TEXT,
                descripcion TEXT,
                grupo_asignacion TEXT,
                fecha_creacion TEXT
            )
            ''')

            # Insertar los datos, verificando que no exista la misma incidencia
            for index, row in df_to_save.iterrows():
                cursor.execute('''
                INSERT OR IGNORE INTO incidencias (numero, centro, caja, descripcion, grupo_asignacion, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (row['Número'], row['Centro'], row['Caja'], row['Breve descripción'], row['Grupo de asignación'], row['Fecha de creación']))

            conn.commit()
            conn.close()

            return redirect(url_for('upload_file_and_show_data'))

    # Cargar los datos de la base de datos y aplicar el filtro de fechas o Castles si es necesario
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_castles = request.args.get('filter_castles')

    conn = sqlite3.connect('incidencias.db')

    # Consulta base para cargar todas las incidencias
    query = 'SELECT * FROM incidencias'
    
    # Lista de condiciones para aplicar filtros
    conditions = []
    
    # Aplicar filtro de rango de fechas si existe
    if start_date and end_date:
        conditions.append(f"fecha_creacion BETWEEN '{start_date}' AND '{end_date}'")
    
    # Aplicar filtro de Castles si está activado
    if filter_castles == 'true':
        query = '''
        SELECT incidencias.*
        FROM incidencias
        JOIN castles ON incidencias.centro = castles.centro AND incidencias.caja = castles.caja
        '''
        # Si ya hay condiciones (como las fechas), se aplicarán después del JOIN
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
    else:
        # Si no hay filtro de Castles, simplemente aplicamos las condiciones de fecha (si las hay)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

    # Ejecutar la consulta
    df = pd.read_sql(query, conn)
    conn.close()

    # Renderizar la tabla como HTML
    table_html = df.to_html(classes='data', index=False)
    
    # Renderizar la página con la tabla, el formulario de fechas y el formulario para subir archivo
    return render_template('index.html', table=table_html, start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
