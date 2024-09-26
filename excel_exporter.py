import pandas as pd
import sqlite3
from io import BytesIO

class ExcelExporter:
    def __init__(self, db_path='incidencias.db'):
        self.db_path = db_path

    def export_to_excel(self, start_date=None, end_date=None, filter_castles=None):
        """Genera un archivo Excel con los datos filtrados según los parámetros proporcionados."""
        conn = sqlite3.connect(self.db_path)

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

        # Guardar el DataFrame en un objeto BytesIO para enviarlo como archivo
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Incidencias')
        output.seek(0)

        # Devolver el archivo Excel en formato BytesIO
        return output
