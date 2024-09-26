import sqlite3

class CastlesManager:
    def __init__(self, db_path='incidencias.db'):
        self.db_path = db_path

    def create_table(self):
        """Crea la tabla Castles en la base de datos si no existe."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS castles (
                centro TEXT,
                caja TEXT,
                fabricante TEXT,
                modelo TEXT,
                numero_serie TEXT,
                fecha_instalacion TEXT,
                PRIMARY KEY (centro, caja)
            )
        ''')
        conn.commit()
        conn.close()

    def insert_castles_data(self, df_castles):
        """Inserta los datos de Castles en la tabla de Castles."""
        # Convertir NaN a cadenas vacías
        df_castles_to_save = df_castles.fillna('')

        # Asegurarse de que las fechas sean cadenas
        df_castles_to_save['Fecha Inst TI LAB1'] = df_castles_to_save['Fecha Inst TI LAB1'].astype(str)

        # Conectar a la base de datos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insertar los datos de Castles
        for index, row in df_castles_to_save.iterrows():
            cursor.execute('''
            INSERT OR IGNORE INTO castles (centro, caja, fabricante, modelo, numero_serie, fecha_instalacion)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (row['Centro'], row['Caja'], row['Fabricantes'], row['Modelo'], row['N/S'], row['Fecha Inst TI LAB1']))

        conn.commit()
        conn.close()
