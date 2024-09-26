from flask import Flask, request, render_template, redirect, url_for, send_file
import sqlite3
import pandas as pd
from io import BytesIO
from castles_manager import CastlesManager
from excel_exporter import ExcelExporter  # Importar la clase ExcelExporter

app = Flask(__name__)

# Crear una instancia de CastlesManager
castles_manager = CastlesManager()

# Crear una instancia de ExcelExporter
excel_exporter = ExcelExporter()

# Ruta principal para subir el archivo de incidencias y mostrar la tabla
@app.route('/', methods=['GET', 'POST'])
def upload_file_and_show_data():
    if request.method == 'POST' and 'file' in request.files:
        # Lógica para subir el archivo sigue igual...
        pass

    # Cargar los datos de la base de datos y aplicar los filtros
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
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
    else:
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

    df = pd.read_sql(query, conn)
    conn.close()

    # Renombrar las columnas para que tengan nombres más legibles
    df = df.rename(columns={
        'numero': 'Número de Incidencia',
        'centro': 'Centro',
        'caja': 'Caja',
        'descripcion': 'Descripción',
        'grupo_asignacion': 'Grupo de Asignación',
        'fecha_creacion': 'Fecha de Creación'
    })

    # Renderizar la tabla como HTML
    table_html = df.to_html(classes='table table-striped table-hover table-bordered', index=False)

    return render_template('index.html', table=table_html, start_date=start_date, end_date=end_date)

# Nueva ruta para exportar la tabla en Excel
@app.route('/export_excel', methods=['GET'])
def export_excel():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_castles = request.args.get('filter_castles')

    # Llamar al método export_to_excel de la clase ExcelExporter
    output = excel_exporter.export_to_excel(start_date, end_date, filter_castles)

    # Construir el nombre del archivo en función de los filtros
    file_name = "incidencias"
    
    if start_date and end_date:
        file_name += f"_{start_date}_to_{end_date}"

    if filter_castles == 'true':
        file_name += "_castles"

    file_name += ".xlsx"  # Añadir la extensión del archivo

    # Enviar el archivo como respuesta con el nombre generado
    return send_file(output, 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name=file_name,  # Usar el nombre dinámico
                     as_attachment=True)



if __name__ == '__main__':
    app.run(debug=True, port=5001)
