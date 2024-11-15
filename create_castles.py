# type: ignore
import sqlite3
from datetime import datetime

import pandas as pd


# Función para formatear la fecha al formato 'YYYY-MM-DD'
def format_date(date_value):
    if pd.isnull(date_value):
        return None
    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d')
    elif isinstance(date_value, str):
        try:
            # Intenta parsear la fecha en diferentes formatos
            date_obj = datetime.strptime(date_value, '%d/%m/%Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(date_value, '%Y-%m-%d')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                return None
    else:
        return None

# Cargar el archivo Excel
file_path = 'Barrido Castles.xlsx'  # Ruta del archivo que has subido
df = pd.read_excel(file_path)

# Asegurarse de que las columnas necesarias están en el DataFrame
required_columns = ['Centro', 'Caja', 'Fecha Instalacion']  # Ajusta el nombre de la columna según tu archivo
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    raise ValueError(f"El archivo Excel no contiene las columnas necesarias: {', '.join(missing_columns)}.")

# Seleccionar las columnas necesarias
df = df[['Centro', 'Caja', 'Fecha Instalacion']]

# Formatear la columna de fecha de instalación
df['Fecha Instalacion'] = df['Fecha Instalacion'].apply(format_date)

# Convertir 'Centro' y 'Caja' a cadenas
df['Centro'] = df['Centro'].astype(str)
df['Caja'] = df['Caja'].astype(str)

# Reemplazar 'nan' por None
df['Centro'] = df['Centro'].replace('nan', None)
df['Caja'] = df['Caja'].replace('nan', None)

# Conectar a la base de datos SQLite
conn = sqlite3.connect('incidencias.db')
cursor = conn.cursor()

# Crear la tabla 'castles' si no existe, incluyendo 'fecha_instalacion'
cursor.execute('''
CREATE TABLE IF NOT EXISTS castles (
    centro TEXT,
    caja TEXT,
    fecha_instalacion TEXT,
    PRIMARY KEY (centro, caja)
)
''')

# Insertar los datos en la tabla 'castles'
for index, row in df.iterrows():
    centro = row['Centro']
    caja = row['Caja']
    fecha_instalacion = row['Fecha Instalacion']

    # Si 'Centro' o 'Caja' son None o 'nan', omitir la fila
    if centro is None or centro == 'nan' or caja is None or caja == 'nan':
        print(f"Fila {index} omitida debido a valores nulos en 'Centro' o 'Caja'")
        continue

    cursor.execute('''
    INSERT OR REPLACE INTO castles (centro, caja, fecha_instalacion)
    VALUES (?, ?, ?)
    ''', (centro, caja, fecha_instalacion))

# Confirmar los cambios
conn.commit()
conn.close()

print("Datos insertados correctamente en la tabla 'castles'")
