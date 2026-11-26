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

On the **Crop Card Image** page, upload one or more images. Each image appears
in a responsive list row with a preview and its own edit, download, and save
controls. Images are preselected for the bulk actions and automatically checked
for a card outline; each row shows a green detected or red not-detected status.
Use **Download grid** to combine selected images using their current crop and
rotation settings. The browser uses `ceil(sqrt(N))` columns and only the rows
needed, with white gaps and any unused cells. Detected outlines are cropped
automatically; manual crop is used only after selecting **Edit crop**. **Cancel
crop** returns that image to the uncropped source.
Select **Edit crop** to open manual adjustment inline to the right of that
image's preview and controls. Rotate the image with the slider or enter an angle
from -180 to 180 degrees in the box above it. Drag the corner handles to fit the
card, or drag inside the outline to move it; the crop outline follows the image
as it rotates. Confirming the crop applies perspective correction. Saving
creates a card named from its uploaded filename.

For low-contrast borders, open **Guided detection** from the editor. Choose the
border shape, direction, and lighting, then preview CLAHE contrast enhancement
and the resulting edge mask. Adjust adaptive-threshold and morphology settings,
run detection, and use the feedback buttons to refine the settings. This
detection runs locally in the browser with OpenCV; no image is uploaded to a
model service.

testing user
jaxe
a1a1a1a1
