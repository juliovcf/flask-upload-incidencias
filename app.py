from flask import Flask, request, render_template, redirect, url_for, flash
import sqlite3
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret_key_for_flask_flash_messages"  # Necesario para usar mensajes flash en Flask

# Ruta principal para subir el archivo y mostrar la tabla
@app.route('/', methods=['GET', 'POST'])
def upload_file_and_show_data():
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file:
            try:
                # Procesar el archivo Excel
                df = pd.read_excel(file)

                # Asegurarse de que las columnas necesarias existen en el archivo Excel
                if 'Ubicación' not in df.columns or 'CI impactado' not in df.columns or 'Número' not in df.columns:
                    flash('El archivo Excel no contiene las columnas necesarias. Asegúrate de que tiene las columnas: "Ubicación", "CI impactado", "Número".', 'error')
                    return redirect(url_for('upload_file_and_show_data'))

                # Extraer "Centro", "Caja" y "Síntoma"
                df['Centro'] = df['Ubicación'].str.extract(r'(\d+)')
                df['Caja'] = df['CI impactado'].str.extract(r'(caj\d+)')

                # Seleccionar las columnas que queremos guardar y añadir la columna "Síntoma"
                df_to_save = df[['Número', 'Centro', 'Caja', 'Breve descripción', 'Grupo de asignación', 'Fecha de creación', 'Síntoma']]

                # Convertir los NaN en cadenas vacías
                df_to_save = df_to_save.fillna('')

                # Asegurarse de que la fecha sea una cadena
                df_to_save['Fecha de creación'] = df_to_save['Fecha de creación'].astype(str)

                # Conectar a la base de datos
                conn = sqlite3.connect('incidencias.db')
                cursor = conn.cursor()

                # Crear la tabla si no existe, incluyendo la columna "Síntoma"
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS incidencias (
                    numero TEXT PRIMARY KEY,
                    centro TEXT,
                    caja TEXT,
                    descripcion TEXT,
                    sintoma TEXT,
                    grupo_asignacion TEXT,
                    fecha_creacion TEXT
                )
                ''')

                # Insertar los datos, verificando que no exista la misma incidencia
                for index, row in df_to_save.iterrows():
                    cursor.execute('''
                    INSERT OR IGNORE INTO incidencias (numero, centro, caja, descripcion, sintoma, grupo_asignacion, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (row['Número'], row['Centro'], row['Caja'], row['Breve descripción'], row['Síntoma'], row['Grupo de asignación'], row['Fecha de creación']))

                conn.commit()
                conn.close()

                flash('Datos insertados correctamente en la base de datos.', 'success')
                return redirect(url_for('upload_file_and_show_data'))

            except Exception as e:
                flash(f'Error al procesar el archivo: {str(e)}', 'error')
                return redirect(url_for('upload_file_and_show_data'))

    # Cargar los datos de la base de datos y aplicar el filtro de fechas si es necesario
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_castles = request.args.get('filter_castles')

    conn = sqlite3.connect('incidencias.db')
    query = 'SELECT * FROM incidencias'
    
    # Filtrar por rango de fechas si está presente
    conditions = []
    if start_date and end_date:
        conditions.append(f"fecha_creacion BETWEEN '{start_date}' AND '{end_date}'")

    # Filtrar por Castles si está activado
    if filter_castles == 'true':
        query = '''
        SELECT incidencias.*
        FROM incidencias
        JOIN castles ON incidencias.centro = castles.centro AND incidencias.caja = castles.caja
        '''
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
    else:
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

    try:
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            flash('No se encontraron incidencias en la base de datos.', 'warning')

        # Renombrar las columnas para que tengan nombres más legibles
        df = df.rename(columns={
            'numero': 'Número de Incidencia',
            'centro': 'Centro',
            'caja': 'Caja',
            'descripcion': 'Descripción',
            'sintoma': 'Síntoma',
            'grupo_asignacion': 'Grupo de Asignación',
            'fecha_creacion': 'Fecha de Creación'
        })

        # Renderizar la tabla como HTML, incluso si está vacía
        table_html = df.to_html(classes='table table-striped table-hover table-bordered', index=False)

    except Exception as e:
        flash(f'Error al cargar los datos: {str(e)}', 'error')
        table_html = '<p>No se pueden mostrar los datos en este momento.</p>'

    # Renderizar la página con la tabla, el formulario de fechas y el formulario para subir archivo
    return render_template('index.html', table=table_html, start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
