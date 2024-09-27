from flask import Flask, request, render_template, redirect, url_for, flash, send_file
import sqlite3
import pandas as pd
from io import BytesIO
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

DATABASE = 'incidencias.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos si no existe."""
    with get_db_connection() as conn:
        conn.execute('''
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
        conn.execute('''
        CREATE TABLE IF NOT EXISTS castles (
            centro TEXT,
            caja TEXT,
            fecha_instalacion TEXT,
            PRIMARY KEY (centro, caja)
        )
        ''')
        conn.commit()

@app.route('/', methods=['GET', 'POST'])
def upload_file_and_show_data():
    init_db()  # Inicializar la base de datos

    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file:
            try:
                # Procesar el archivo Excel
                df = pd.read_excel(file)

                # Verificar que las columnas necesarias existen
                required_columns = ['Ubicación', 'CI impactado', 'Número', 'Breve descripción', 'Grupo de asignación', 'Fecha de creación', 'Síntoma']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f'El archivo Excel no contiene las columnas necesarias: {", ".join(missing_columns)}.', 'danger')
                    return redirect(url_for('upload_file_and_show_data'))

                # Extraer "Centro", "Caja" y "Síntoma"
                df['Centro'] = df['Ubicación'].str.extract(r'(\d+)', expand=False)
                df['Caja'] = df['CI impactado'].str.extract(r'(caj\d+)', expand=False)

                # Seleccionar las columnas que queremos guardar
                df_to_save = df[['Número', 'Centro', 'Caja', 'Breve descripción', 'Síntoma', 'Grupo de asignación', 'Fecha de creación']]

                # Convertir los NaN en cadenas vacías y asegurar tipos
                df_to_save = df_to_save.fillna('')
                df_to_save['Fecha de creación'] = df_to_save['Fecha de creación'].astype(str)

                # Conectar a la base de datos y guardar los datos
                with get_db_connection() as conn:
                    cursor = conn.cursor()

                    # Crear la tabla si no existe
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
                        ''', (
                            row['Número'],
                            row['Centro'],
                            row['Caja'],
                            row['Breve descripción'],
                            row['Síntoma'],
                            row['Grupo de asignación'],
                            row['Fecha de creación']
                        ))

                    conn.commit()

                flash('Datos insertados correctamente en la base de datos.', 'success')
                return redirect(url_for('upload_file_and_show_data'))

            except Exception as e:
                flash(f'Error al procesar el archivo: {str(e)}', 'danger')
                return redirect(url_for('upload_file_and_show_data'))

    # Manejo de solicitudes GET y otras situaciones
    # Obtener los parámetros de filtrado
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_castles = request.args.get('filter_castles')

    # Construir la consulta SQL
    query = 'SELECT * FROM incidencias'
    params = []
    conditions = []

    if start_date and end_date:
        conditions.append("fecha_creacion BETWEEN ? AND ?")
        params.extend([start_date, end_date])

    if filter_castles == 'true':
        query = '''
        SELECT incidencias.*
        FROM incidencias
        JOIN castles ON incidencias.centro = castles.centro AND incidencias.caja = castles.caja
        WHERE date(castles.fecha_instalacion) <= date(incidencias.fecha_creacion)
        '''
        if conditions:
            query += ' AND ' + ' AND '.join(conditions)
    else:
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

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

        # Convertir el DataFrame a una lista de diccionarios
        data = df.to_dict(orient='records')
        columns = df.columns.tolist()

    except Exception as e:
        flash(f'Error al cargar los datos: {str(e)}', 'danger')
        data = []
        columns = []

    return render_template('index.html', data=data, columns=columns, start_date=start_date, end_date=end_date)


@app.route('/export_excel', methods=['GET'])
def export_excel():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_castles = request.args.get('filter_castles')

    # Construir la consulta SQL
    query = 'SELECT * FROM incidencias'
    params = []
    conditions = []

    if start_date and end_date:
        conditions.append("fecha_creacion BETWEEN ? AND ?")
        params.extend([start_date, end_date])

    if filter_castles == 'true':
        query = '''
        SELECT incidencias.*
        FROM incidencias
        JOIN castles ON incidencias.centro = castles.centro AND incidencias.caja = castles.caja
        WHERE date(castles.fecha_instalacion) <= date(incidencias.fecha_creacion)
        '''
        if conditions:
            query += ' AND ' + ' AND '.join(conditions)
    else:
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        # Renombrar las columnas si es necesario
        df = df.rename(columns={
            'numero': 'Número de Incidencia',
            'centro': 'Centro',
            'caja': 'Caja',
            'descripcion': 'Descripción',
            'sintoma': 'Síntoma',
            'grupo_asignacion': 'Grupo de Asignación',
            'fecha_creacion': 'Fecha de Creación'
        })

        # Exportar a Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Incidencias')
        output.seek(0)

        # Construir el nombre del archivo
        file_name = "incidencias"
        if start_date and end_date:
            file_name += f"_{start_date}_to_{end_date}"
        if filter_castles == 'true':
            file_name += "_castles"
        file_name += ".xlsx"

        return send_file(output, 
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         download_name=file_name,
                         as_attachment=True)

    except Exception as e:
        flash(f'Error al exportar los datos: {str(e)}', 'danger')
        return redirect(url_for('upload_file_and_show_data'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
