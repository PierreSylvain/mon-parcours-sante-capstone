import sqlite3
import json
import os
import datetime

class HealthStore:
    def __init__(self, db_path="mon_parcours_sante/data/health.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        
        # profile (singleton)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                pseudonym TEXT,
                birth_year INTEGER,
                mutuelle_name TEXT,
                mutuelle_rate TEXT
            )
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO profile (id, pseudonym, birth_year, mutuelle_name, mutuelle_rate)
            VALUES (1, 'User', NULL, NULL, NULL)
        ''')

        # conditions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT,
                since TEXT,
                source TEXT
            )
        ''')

        # allergies
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allergies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                substance TEXT,
                declared_severity TEXT
            )
        ''')

        # medications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                dose TEXT,
                schedule TEXT,
                prescriber TEXT,
                start_date TEXT,
                renewal_date TEXT,
                prescription_ref TEXT
            )
        ''')

        # providers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                specialty TEXT,
                contact TEXT,
                last_seen TEXT
            )
        ''')

        # documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                date TEXT,
                source TEXT,
                extracted_values TEXT,
                vector_ref TEXT
            )
        ''')

        # lab_values
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lab_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                marker TEXT,
                value TEXT,
                unit TEXT,
                reference_range TEXT,
                date TEXT,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
        ''')

        # appointments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER,
                datetime TEXT,
                reason TEXT,
                brief_ref TEXT,
                FOREIGN KEY(provider_id) REFERENCES providers(id)
            )
        ''')

        # reimbursements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reimbursements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                care_event TEXT,
                date TEXT,
                paid REAL,
                secu_reimbursed REAL,
                mutuelle_reimbursed REAL,
                remaining REAL,
                status TEXT
            )
        ''')

        # audit_log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                field TEXT,
                old_value TEXT,
                new_value TEXT
            )
        ''')

        self.conn.commit()

    def get_profile(self):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM profile WHERE id = 1")
        profile_row = cursor.fetchone()
        profile_data = dict(profile_row) if profile_row else {}

        cursor.execute("SELECT * FROM conditions")
        profile_data['conditions'] = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM allergies")
        profile_data['allergies'] = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM medications")
        profile_data['medications'] = [dict(row) for row in cursor.fetchall()]

        return profile_data

    def search_documents(self, query):
        cursor = self.conn.cursor()
        search_query = f"%{query}%"
        cursor.execute('''
            SELECT * FROM documents
            WHERE type LIKE ? OR source LIKE ? OR extracted_values LIKE ?
        ''', (search_query, search_query, search_query))
        
        results = []
        for row in cursor.fetchall():
            doc = dict(row)
            if doc['extracted_values']:
                try:
                    doc['extracted_values'] = json.loads(doc['extracted_values'])
                except json.JSONDecodeError:
                    pass
            results.append(doc)
        return results

    def get_all_documents(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents")
        results = []
        for row in cursor.fetchall():
            doc = dict(row)
            if doc['extracted_values']:
                try:
                    doc['extracted_values'] = json.loads(doc['extracted_values'])
                except json.JSONDecodeError:
                    pass
            if doc['vector_ref']:
                try:
                    doc['vector_ref'] = json.loads(doc['vector_ref'])
                except json.JSONDecodeError:
                    pass
            results.append(doc)
        return results


    def update_profile(self, field, value):
        allowed_fields = {'pseudonym', 'birth_year', 'mutuelle_name', 'mutuelle_rate'}
        if field not in allowed_fields:
            raise ValueError(f"Field '{field}' is not allowed to be updated.")

        cursor = self.conn.cursor()
        
        cursor.execute(f"SELECT {field} FROM profile WHERE id = 1")
        row = cursor.fetchone()
        old_value = row[field] if row else None

        cursor.execute(f"UPDATE profile SET {field} = ? WHERE id = 1", (value,))
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute('''
            INSERT INTO audit_log (timestamp, field, old_value, new_value)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, field, str(old_value), str(value)))

        self.conn.commit()
        
    def add_document(self, doc_type, date, source, extracted_values):
        cursor = self.conn.cursor()
        extracted_json = json.dumps(extracted_values) if extracted_values else "{}"
        cursor.execute('''
            INSERT INTO documents (type, date, source, extracted_values)
            VALUES (?, ?, ?, ?)
        ''', (doc_type, date, source, extracted_json))
        self.conn.commit()
        return cursor.lastrowid
        
    def add_lab_value(self, document_id, marker, value, unit, reference_range, date):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO lab_values (document_id, marker, value, unit, reference_range, date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (document_id, marker, str(value), unit, reference_range, date))
        self.conn.commit()
        return cursor.lastrowid

    def get_document(self, document_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        if row:
            doc = dict(row)
            if doc['extracted_values']:
                try:
                    doc['extracted_values'] = json.loads(doc['extracted_values'])
                except json.JSONDecodeError:
                    pass
            return doc
        return None

    def set_document_vector(self, document_id: int, vector: list[float]) -> None:
        self.conn.execute(
            "UPDATE documents SET vector_ref = ? WHERE id = ?",
            (json.dumps(vector), document_id),
        )
        self.conn.commit()
        
    def get_marker_timeline(self, marker: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT date, value, unit, reference_range
            FROM lab_values
            WHERE marker COLLATE NOCASE = ?
            ORDER BY date ASC
        ''', (marker,))
        results = [dict(row) for row in cursor.fetchall()]
        return results

    def close(self):
        self.conn.close()
