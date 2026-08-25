from db import get_connection

print('Adding limite_usuarios...')
try:
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute('ALTER TABLE organizaciones ADD COLUMN limite_usuarios INTEGER NOT NULL DEFAULT 3;')
        print('Added limite_usuarios column')
    except Exception as e:
        print('Column might already exist:', e)
        
    cur.close()
    conn.close()
except Exception as e:
    print(f'Database error: {e}')
