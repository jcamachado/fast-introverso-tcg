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

## TCGdex card lookup

On the **Add Card** page, upload a picture to recognize its text in your browser
and get TCGdex suggestions. Select a match to fill in its details; your uploaded
picture is saved with the card. You can edit the detected name and search again.
Install the integration with the other application dependencies using
`pip install -r requirements.txt`.

## Crop adjustment

On the **Crop Card Image** page, select **Manual adjustment** to reveal crop
choices and image rotation controls. Rotate the image with the slider or enter
an angle from -180 to 180 degrees in the box above it. Drag the corner handles
to fit the card, or drag inside the outline to move it; the crop outline follows
the image as it rotates. If automatic detection misses, manual adjustment
creates an adjustable starting outline. Confirming the crop applies perspective
correction.

testing user
jaxe
a1a1a1a1
