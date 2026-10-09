"""Initialize an empty database. No synthetic test results are inserted."""
import os
from database.db import init_db

if __name__ == '__main__':
    path=os.getenv('DATABASE_PATH','whynet.db')
    init_db(path)
    print(f'Initialized database at {path}')
