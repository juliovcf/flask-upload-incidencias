# type: ignore
import os
import sqlite3
from io import BytesIO

import pandas as pd
from flask import (Flask, flash, redirect, render_template, request, send_file,
                   url_for)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

DATABASE = 'incidencias.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS incidencias (
            numero TEXT PRIMARY KEY,
            centro TEXT,
            caja TEXT,
            descripcion TEXT,
            breve_descripcion TEXT,
            sintoma TEXT,
            grupo_asignacion TEXT,
            id_correlacion TEXT,
            fabricante TEXT,
            resolucion TEXT,
            fecha_creacion TEXT,
            tipo_incidencia TEXT DEFAULT ''
        )
        ''')

        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(incidencias)")
        columns = [col[1] for col in cursor.fetchall()]
        # Si la columna `tipo_incidencia` no existe, la añadimos a la tabla existente
        if 'tipo_incidencia' not in columns:
            cursor.execute("ALTER TABLE incidencias ADD COLUMN tipo_incidencia TEXT DEFAULT ''")
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
                required_columns = ['Ubicación', 'CI impactado', 'Número', 'Descripción', 'Breve descripción', 'Síntoma', 'Grupo de asignación', ' Notas de resolución', 'Fecha de creación']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f'El archivo Excel no contiene las columnas necesarias: {", ".join(missing_columns)}.', 'danger')
                    return redirect(url_for('upload_file_and_show_data'))

                # Extraer "Centro", "Caja" y "Síntoma"
                df['Centro'] = df['Ubicación'].str.extract(r'(\d+)', expand=False)
                df['Caja'] = df['CI impactado'].str.extract(r'(caj\d+)', expand=False)

                # Seleccionar las columnas que queremos guardar
                df_to_save = df[['Número', 'Centro', 'Caja', 'Descripción', 'Breve descripción', 'Síntoma', 'Grupo de asignación', 'ID de correlación', 'Fabricante', ' Notas de resolución', 'Fecha de creación']]

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
                        breve_descripcion TEXT,
                        sintoma TEXT,
                        grupo_asignacion TEXT,
                        id_correlacion TEXT,
                        fabricante TEXT,
                        resolucion TEXT,
                        fecha_creacion TEXT,
                        tipo_incidencia TEXT DEFAULT ''
                    )
                    ''')

                # Insertar los datos, verificando que no exista la misma incidencia
                for index, row in df_to_save.iterrows():
                    cursor.execute('''
                    INSERT INTO incidencias (numero, centro, caja, descripcion, breve_descripcion, sintoma, grupo_asignacion, id_correlacion, fabricante, resolucion, fecha_creacion, tipo_incidencia)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(numero) DO UPDATE SET
                        centro = excluded.centro,
                        caja = excluded.caja,
                        descripcion = excluded.descripcion,
                        breve_descripcion = excluded.breve_descripcion,
                        sintoma = excluded.sintoma,
                        grupo_asignacion = excluded.grupo_asignacion,
                        id_correlacion = excluded.id_correlacion,
                        fabricante = excluded.fabricante,
                        resolucion = excluded.resolucion,
                        fecha_creacion = excluded.fecha_creacion
                    ''', (
                        row['Número'],
                        row['Centro'],
                        row['Caja'],
                        row['Descripción'],
                        row['Breve descripción'],
                        row['Síntoma'],
                        row['Grupo de asignación'],
                        row['ID de correlación'],
                        row['Fabricante'],
                        row[' Notas de resolución'],
                        row['Fecha de creación'],
                        ''  # Nuevo valor por defecto para tipo_incidencia
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
    query = 'SELECT numero, centro, caja, breve_descripcion, sintoma, grupo_asignacion, fabricante, resolucion, fecha_creacion, tipo_incidencia FROM incidencias'
    params = []
    conditions = []

    if start_date and end_date:
        conditions.append("fecha_creacion >= ? AND fecha_creacion <= ? || ' 23:59:59'")
        params.extend([start_date, end_date])

    if filter_castles == 'true':
        query = '''
        SELECT numero, incidencias.centro, incidencias.caja, breve_descripcion, sintoma, grupo_asignacion, fabricante, resolucion, fecha_creacion, tipo_incidencia
        FROM incidencias
        JOIN castles ON incidencias.centro = castles.centro AND incidencias.caja = castles.caja
        WHERE date(castles.fecha_instalacion) <= date(incidencias.fecha_creacion)
        '''
        if conditions:
            query += ' AND ' + ' AND '.join(conditions)
    else:
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

    # Ordenamos por fecha
    query += ' ORDER BY fecha_creacion'

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
            'breve_descripcion': 'Breve Descripción',
            'sintoma': 'Síntoma',
            'grupo_asignacion': 'Grupo de Asignación',
            'id_correlacion': 'ID de Correlación',
            'fabricante': 'Fabricante',
            'resolucion': 'Resolución',
            'fecha_creacion': 'Fecha de Creación',
            'tipo_incidencia': 'Tipo de Incidencia'
        })

        # Convertir el DataFrame a una lista de diccionarios
        data = df.to_dict(orient='records')
        columns = df.columns.tolist()

    except Exception as e:
        flash(f'Error al cargar los datos: {str(e)}', 'danger')
        data = []
        columns = []

    return render_template('index.html', data=data, columns=columns, start_date=start_date, end_date=end_date, filter_castles=filter_castles)

@app.route('/update_tipo_incidencia/<numero>', methods=['POST'])
def update_tipo_incidencia(numero):
    tipo_incidencia = request.form.get('tipo_incidencia')
    if not tipo_incidencia:
        tipo_incidencia = ''  # Permitir que se seleccione el valor vacío

    # Recuperar los parámetros de filtrado para mantener el estado
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    filter_castles = request.form.get('filter_castles')

    try:
        with get_db_connection() as conn:
            conn.execute('''
            UPDATE incidencias
            SET tipo_incidencia = ?
            WHERE numero = ?
            ''', (tipo_incidencia, numero))
            conn.commit()

        flash(f'Tipo de incidencia actualizado correctamente para la incidencia {numero}.', 'success')

    except Exception as e:
        flash(f'Error al actualizar el tipo de incidencia: {str(e)}', 'danger')

    # Redirigir manteniendo los parámetros de filtrado
    return redirect(url_for('upload_file_and_show_data', start_date=start_date, end_date=end_date, filter_castles=filter_castles))

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
        conditions.append("fecha_creacion >= ? AND fecha_creacion <= ? || ' 23:59:59'")
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
            'breve_descripcion': 'Breve Descripción',
            'sintoma': 'Síntoma',
            'grupo_asignacion': 'Grupo de Asignación',
            'id_correlacion': 'ID de Correlación',
            'fabricante': 'Fabricante',
            'resolucion': 'Resolución',
            'fecha_creacion': 'Fecha de Creación',
            'tipo_incidencia': 'Tipo de Incidencia'
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
