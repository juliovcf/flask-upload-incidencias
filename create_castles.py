import sqlite3
import pandas as pd

# Cargar el archivo Excel
file_path = 'Barrido Castles.xlsx'  # Ruta del archivo que has subido
df = pd.read_excel(file_path)

# Asegurarse de que las columnas Centro y Caja están en el DataFrame
# Cambia los nombres de las columnas si son diferentes en tu archivo Excel
df = df[['Centro', 'Caja']]

# Conectar a la base de datos SQLite
conn = sqlite3.connect('incidencias.db')
cursor = conn.cursor()

# Crear la tabla 'castles' si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS castles (
    centro TEXT,
    caja TEXT,
    PRIMARY KEY (centro, caja)
)
''')

# Insertar los datos en la tabla 'castles'
for index, row in df.iterrows():
    cursor.execute('''
    INSERT OR IGNORE INTO castles (centro, caja)
    VALUES (?, ?)
    ''', (row['Centro'], row['Caja']))

# Confirmar los cambios
conn.commit()
conn.close()

print("Datos insertados correctamente en la tabla 'castles'")
