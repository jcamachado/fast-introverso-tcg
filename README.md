# fast-introverso-tcg

source /home/jaxe/Repositories/fasttcg/fast-introverso-tcg/venv/bin/activate

sqlite3 tcg.db ".schema users"
source /home/jaxe/Repositories/fasttcg/fast-introverso-tcg/venv/bin/activate

# Confirm no other data before deleting

sqlite3 tcg.db "SELECT id, username FROM users;"

# Nuke it and let create_all() rebuild from the current model

rm tcg.db
uvicorn app.main:app --reload

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

testing user
jaxe
a1a1a1a1
