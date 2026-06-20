import importlib.util
import os
import json
from pathlib import Path

def load_store_module():
    # Load store.py without importing the mon_parcours_sante package
    file_path = Path("mon_parcours_sante/store.py").resolve()
    spec = importlib.util.spec_from_file_location("store", str(file_path))
    store_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(store_module)
    return store_module

def main():
    store_module = load_store_module()
    
    db_path = "mon_parcours_sante/data/health.db"
    store = store_module.HealthStore(db_path)
    
    cursor = store.conn.cursor()
    
    # Update profile
    cursor.execute('''
        UPDATE profile
        SET pseudonym = ?, birth_year = ?, mutuelle_name = ?, mutuelle_rate = ?
        WHERE id = 1
    ''', ('Moi', 1990, 'Harmonie Mutuelle', '0.8'))
    
    # Insert condition
    cursor.execute('''
        INSERT INTO conditions (label, since, source)
        VALUES (?, ?, ?)
    ''', ('Hypothyroïdie', '2021', 'déclaré'))
    
    # Insert allergy
    cursor.execute('''
        INSERT INTO allergies (substance, declared_severity)
        VALUES (?, ?)
    ''', ('Pénicilline', 'modérée'))
    
    # Insert medication
    cursor.execute('''
        INSERT INTO medications (name, dose, schedule, prescriber, start_date, renewal_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('Lévothyrox', '75 µg', '1/jour le matin', 'Dr Martin', '2021-03-01', '2026-07-15'))
    
    # Insert document
    extracted_values = json.dumps({
        "TSH": {
            "value": 5.2, 
            "unit": "mUI/L", 
            "reference_range": "0.27-4.2"
        }
    })
    cursor.execute('''
        INSERT INTO documents (type, date, extracted_values)
        VALUES (?, ?, ?)
    ''', ('bilan thyroïdien', '2026-05-10', extracted_values))
    
    store.conn.commit()
    
    profile_data = store.get_profile()
    store.close()
    
    print(f"Database seeded successfully at: {Path(db_path).resolve()}")
    print("Resulting profile:")
    print(json.dumps(profile_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
