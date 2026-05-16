import json
from pathlib import Path

import cv2

ROOT = Path(r"D:\GTVT\ChuyenDePhatTrienHeThongThongMinh\Assignments\Code\Parking-Space-Detection-System")

IMAGE_PATH = ROOT / "datasets" / "emty.png"
COORD_PATH = ROOT / "infra" / "slot-coordinates.json"
OUTPUT_PATH = ROOT / "datasets" / "slot_overlay_generated.png"

img = cv2.imread(str(IMAGE_PATH))
if img is None:
    raise FileNotFoundError(IMAGE_PATH)

with open(COORD_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

colors = {
    "A": (0, 255, 0),
    "B": (255, 180, 0),
    "C": (0, 140, 255),
}

for slot in data["slots"]:
    slot_id = slot["slot_id"]
    zone = slot_id[0]

    x = int(slot["x"])
    y = int(slot["y"])
    w = int(slot["w"])
    h = int(slot["h"])

    color = colors.get(zone, (255, 255, 255))

    cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
    cv2.putText(
        img,
        slot_id,
        (x + 4, y + 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        color,
        1,
        cv2.LINE_AA,
    )

cv2.imwrite(str(OUTPUT_PATH), img)
print(f"Saved: {OUTPUT_PATH}")
