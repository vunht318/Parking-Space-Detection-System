import cv2
import os

# 👉 video của bạn nằm trong uploads
video_path = "carPark.mp4"

# 👉 nơi lưu ảnh
output_folder = "img"

# 👉 tạo folder nếu chưa có
os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)

frame_count = 0
saved_count = 400

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # 👉 lấy mỗi 10 frame
    if frame_count % 10 == 0:

        filename = f"{output_folder}/img_{saved_count}.jpg"

        cv2.imwrite(filename, frame)

        print("Saved:", filename)

        saved_count += 1

    frame_count += 1

cap.release()

print("DONE! Total images:", saved_count)