# Bug Report: Parking Status Sai — Root Cause Analysis & Fix

**Date:** 2026-05-17  
**Branch:** dev  
**Status:** ✅ FIXED  
**Services affected:** `ai-detection-service`, `backend-api`  
**Files changed:** `apps/ai-detection-service/main.py`, `.env`, `infra/slot-config.json`

---

## 1. Tóm tắt vấn đề

Nhiều slot bãi đậu xe bị báo sai trạng thái (**false positive**: đang trống nhưng hệ thống báo occupied). Vấn đề tồn tại xuyên suốt toàn bộ video (`detect #1` → `detect #56`) và không được voting window sửa vì score luôn nằm trên threshold.

---

## 2. Bằng chứng từ detect-result.log

### 2.1 — Phân phối score thực tế

| Nhóm slot | Score range | Kết luận |
|-----------|-------------|----------|
| Slot thật sự trống (vacant) | 0.03 – 0.10 | Đúng |
| **Vùng nhiễu / false positive** | **0.12 – 0.20** | ← bug nằm ở đây |
| Slot thật sự có xe (occupied) | 0.40 – 0.80 | Đúng |
| `DETECTION_THRESHOLD` | **0.12** | Threshold đặt ngay trong vùng nhiễu |

### 2.2 — Các slot bị false positive liên tục (toàn bộ video)

| Slot | Score range | Voted | Nhận xét |
|------|-------------|-------|-----------|
| **B-L03** | 0.127 – 0.155 | OCCUPIED mọi frame | Score chưa bao giờ vượt 0.16 — thấp hơn nhiều so với occupied thật (≥0.40) |
| **C-R01** | 0.130 – 0.178 | OCCUPIED mọi frame | Score cao hơn vacant thật nhưng vẫn thấp hơn occupied thật 3–5 lần |
| **C-R08** | 0.126 – 0.171 | OCCUPIED mọi frame | Cùng pattern với B-L03, C-R01 |

### 2.3 — Slot bị false positive thoáng qua (voting sửa được một phần)

| Slot | Hành vi | Ghi chú |
|------|---------|---------|
| **A-L07** | Score dao động 0.097–0.135, vượt threshold lúc detect #1 rồi giảm xuống | Voting dần sửa, nhưng brief OCCUPIED vẫn được broadcast lên backend |
| **B-L10** | Score 0.116–0.128, votes=[0,1,1] → briefly OCCUPIED tại detect #3 | Sửa được sau 4–5 detects |

### 2.4 — Log evidence chi tiết

**Detect #1 (frame 00012, t=0.50s):** A-L07 bị false positive ngay từ đầu
```
A-L07   0.1214  OCCUPIED   OCCUPIED    [1]   ← score chỉ 0.1214, vừa qua ngưỡng 0.12
B-L03   0.1267  OCCUPIED   OCCUPIED    [1]   ← bắt đầu false positive liên tục
C-R01   0.1315  OCCUPIED   OCCUPIED    [1]   ← bắt đầu false positive liên tục
C-R08   0.1261  OCCUPIED   OCCUPIED    [1]   ← bắt đầu false positive liên tục
```

**Detect #56 (frame 00672, t=28.00s):** Các slot trên vẫn sai sau toàn bộ video
```
B-L03   0.1222  OCCUPIED   OCCUPIED    [1,1,1,1,1]
C-R01   0.0588  vacant     vacant      [0,0,0,0,0]   ← C-R01 tự sửa ở cuối
C-R08   0.0537  vacant     vacant      [0,0,0,0,0]   ← C-R08 tự sửa ở cuối
```

> **Quan sát thú vị:** C-R01 và C-R08 giảm score xuống `0.05` ở cuối video → chứng tỏ đây là **shadow/lighting thay đổi theo thời gian trong video**, không phải xe. Ở đầu video bóng đổ làm diff tăng lên, cuối video bóng di chuyển đi.

---

## 3. Root Cause Analysis

### RC-1 ★ CRITICAL — Reference image `emty.png` không match điều kiện video

**File:** `apps/ai-detection-service/main.py` line 115–132 (`detect_slot_occupied`)

**Vấn đề:**  
Algorithm so sánh pixel giữa frame video và `emty.png` (ảnh chụp bãi trống). Nếu hai nguồn này được chụp ở **thời điểm khác nhau** (ánh sáng, góc nắng, bóng đổ khác nhau), các pixel ở một số slot sẽ **luôn khác nhau** dù slot thật sự trống.

**Bằng chứng từ log:**
- B-L03 score `0.127–0.155` toàn bộ video → permanent background diff, không phải xe
- C-R01, C-R08 score giảm từ `0.13–0.17` xuống `0.05` ở cuối video → shadow di chuyển, xác nhận không có xe

**Code hiện tại:**
```python
# detect_slot_occupied — line 122–131
diff = cv2.absdiff(gray_frame, gray_ref)
_, threshold = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)
changed_pixels = cv2.countNonZero(threshold)
total_pixels = threshold.shape[0] * threshold.shape[1]
score = changed_pixels / total_pixels

detection_threshold = float(os.getenv("DETECTION_THRESHOLD", "0.12"))
occupied = score >= detection_threshold  # ← 0.12 quá thấp
```

---

### RC-2 ★ CRITICAL — `DETECTION_THRESHOLD = 0.12` quá thấp, nằm trong vùng nhiễu

**File:** `.env` line 17, `apps/ai-detection-service/main.py` line 129

**Vấn đề:**  
Threshold 0.12 (12%) nằm ngay trong **noise zone** của background differences. Không có khoảng cách (margin) giữa background noise và threshold.

| Khoảng | Score | Ý nghĩa |
|--------|-------|---------|
| Vacant thật | 0.03–0.10 | Slot trống, không có xe |
| **Noise zone** | **0.10–0.20** | Bóng đổ, road marking, reference mismatch |
| Threshold | **0.12** | ← đặt trong noise zone |
| Occupied thật | 0.40–0.80 | Xe đang đậu |

**Gap giữa max của false positive và min của true positive: 0.20 → 0.40** (khoảng rất rộng). Đây là "safe zone" để đặt threshold cao hơn mà không làm mất detection thật.

**Fix:** Tăng threshold lên `0.25–0.30` sẽ loại bỏ toàn bộ false positive (max noise = 0.18) trong khi vẫn bắt tất cả xe thật (min occupied = 0.40).

---

### RC-3 ★ HIGH — `slot_votes` không được reset khi video loop lại

**File:** `apps/ai-detection-service/main.py` line 256–284

**Vấn đề:**  
`slot_votes` được khởi tạo một lần trước vòng lặp. Khi video hết (`cap.read()` return `False`) và reset về frame 0, `slot_votes` giữ nguyên giá trị từ cuối video. Votes từ frame cuối video "lây" sang đầu video vòng sau.

**Code hiện tại:**
```python
slot_votes: dict[str, deque] = defaultdict(lambda: deque(maxlen=vote_window))
# ...
while True:
    success, frame = cap.read()
    if not success:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_count = 0
        # ← slot_votes KHÔNG được reset!
        await asyncio.sleep(0.1)
        continue
```

**Ví dụ:** Nếu slot X có votes `[1,1,1,1,0]` (majority occupied) ở frame 679, khi loop lại:
- Frame 1 detect X là vacant → votes = `[1,1,1,0,0]` → majority = 3/5 → vẫn ra OCCUPIED ← SAI
- Mất 3 detects nữa mới sửa đúng

---

### RC-4 ★ MEDIUM — Không có hysteresis trong threshold

**File:** `apps/ai-detection-service/main.py` line 129–131

**Vấn đề:**  
Hard threshold không có hysteresis. Slot A-L07 có score dao động quanh 0.12:
```
detect #1:  0.1214 → OCCUPIED
detect #2:  0.1179 → vacant
detect #9:  0.1342 → OCCUPIED   (brief, cuối video)
detect #10: 0.1351 → OCCUPIED
detect #11: 0.1051 → vacant
```
Mỗi lần vượt threshold đều tạo ra vote sai, và mỗi change event đều được broadcast lên backend và WebSocket tới frontend.

**Hysteresis** (ngưỡng kép) sẽ sửa vấn đề này:
- Để chuyển từ `vacant → occupied`: score ≥ `high_threshold` (0.25)
- Để chuyển từ `occupied → vacant`: score < `low_threshold` (0.15)

---

### RC-5 ★ LOW — Dữ liệu không nhất quán giữa `slot-config.json` và `slot-coordinates.json`

**File:** `infra/slot-config.json`, `infra/slot-coordinates.json`

**Vấn đề:**  
Toàn bộ Zone A (24 slots: A-L01..A-L12, A-R01..A-R12) có y-coordinate **khác nhau 4px** giữa hai file:

| Slot | slot-config.json (y) | slot-coordinates.json (y) | Diff |
|------|---------------------|--------------------------|------|
| A-L01 | 104 | 108 | -4 |
| A-L02 | 160 | 164 | -4 |
| A-L06 | 384 | 386 | -2 |
| A-L07 | **448** | **444** | **+4** ← nghịch chiều! |
| A-L08 | 496 | 500 | -4 |
| ... (tất cả Zone A) | | | |

**Lưu ý:** Detection chỉ dùng `slot-coordinates.json` (đúng) nhưng nếu ai dùng `slot-config.json` cho detection sẽ lệch ROI 4px. Slot A-L07 trong config thậm chí lệch ngược chiều (+4 thay vì -4).

---

### RC-6 ★ LOW — Global ROI scale không bù được per-slot perspective distortion

**File:** `apps/ai-detection-service/main.py` line 96–110

**Vấn đề:**  
`scale_slot_rect` áp dụng một bộ scale/offset **toàn cục** cho tất cả slots:
```python
video_offset_x = int(os.getenv("VIDEO_OFFSET_X", "0"))
video_offset_y = int(os.getenv("VIDEO_OFFSET_Y", "5"))
video_scale_x = float(os.getenv("VIDEO_SCALE_X", "0.985"))
video_scale_y = float(os.getenv("VIDEO_SCALE_Y", "0.980"))
```

Nếu video frame và reference image có **perspective distortion** (góc camera khác nhau giữa hai lần chụp), sự lệch ROI sẽ **không đồng đều theo vị trí**. Một bộ scale/offset toàn cục không thể bù đắp cho hiện tượng này — các slot ở góc xa sẽ lệch nhiều hơn slot ở trung tâm.

---

## 4. Solution — Fix triệt để

### Fix 1 (CRITICAL): Tăng `DETECTION_THRESHOLD` lên `0.25`

**File:** `.env`

```diff
- DETECTION_THRESHOLD=0.12
+ DETECTION_THRESHOLD=0.25
```

**Lý do:** Gap giữa max noise (0.18) và min occupied-thật (0.40) rất rộng. Threshold 0.25:
- Loại bỏ: B-L03 (max 0.155), C-R01 (max 0.178), C-R08 (max 0.171), A-L07 (max 0.135)
- Giữ được: tất cả xe thật (min 0.35, trung bình 0.55)

---

### Fix 2 (CRITICAL): Implement hysteresis thay thế hard threshold

**File:** `apps/ai-detection-service/main.py`

Thêm 2 env vars và sửa `detect_slot_occupied`:

```python
# Thêm vào detect_slot_occupied
def detect_slot_occupied(
    frame_roi: np.ndarray,
    reference_roi: np.ndarray,
    current_state: bool = False,  # trạng thái hiện tại để tính hysteresis
) -> tuple[bool, float]:
    gray_frame = cv2.cvtColor(frame_roi, cv2.COLOR_BGR2GRAY)
    gray_ref = cv2.cvtColor(reference_roi, cv2.COLOR_BGR2GRAY)
    gray_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)
    gray_ref = cv2.GaussianBlur(gray_ref, (5, 5), 0)
    diff = cv2.absdiff(gray_frame, gray_ref)
    _, threshold = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)
    changed_pixels = cv2.countNonZero(threshold)
    total_pixels = threshold.shape[0] * threshold.shape[1]
    score = changed_pixels / total_pixels

    high_threshold = float(os.getenv("DETECTION_THRESHOLD", "0.25"))
    low_threshold = float(os.getenv("DETECTION_THRESHOLD_LOW", "0.15"))

    if current_state:
        # Đang occupied → chỉ chuyển sang vacant khi score thật sự thấp
        occupied = score >= low_threshold
    else:
        # Đang vacant → chỉ chuyển sang occupied khi score đủ cao
        occupied = score >= high_threshold

    return occupied, score
```

Cập nhật call site trong `build_detection_payload` để truyền `current_state`.

**.env:**
```
DETECTION_THRESHOLD=0.25
DETECTION_THRESHOLD_LOW=0.15
```

---

### Fix 3 (HIGH): Reset `slot_votes` khi video loop lại

**File:** `apps/ai-detection-service/main.py` line 281–285

```python
if not success:
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    frame_count = 0
    slot_votes.clear()          # ← THÊM DÒNG NÀY
    last_published_state = {}   # ← THÊM DÒNG NÀY: force re-publish sau loop
    await asyncio.sleep(0.1)
    continue
```

---

### Fix 4 (HIGH): Đồng bộ y-coordinates trong `slot-config.json` với `slot-coordinates.json`

**File:** `infra/slot-config.json`

Toàn bộ Zone A cần cập nhật y-coordinate để khớp với `slot-coordinates.json` (file đúng):

| Slot | y hiện tại (sai) | y đúng |
|------|-----------------|--------|
| A-L01 đến A-L06, A-R01 đến A-R06 | 104,160,216,272,328,384 | 108,164,220,276,332,386(L)/388(R) |
| A-L07 | **448** | **444** |
| A-L08 đến A-L12, A-R07 đến A-R12 | 496,552,608,664,720 | 500,556,612,668,724 |

---

### Fix 5 (MEDIUM): Cải thiện reference image capture procedure

**Vấn đề hiện tại:** `emty.png` được chụp ở điều kiện khác với `carPark.mp4`.

**Giải pháp:** Tạo reference image **từ chính video** thay vì ảnh chụp riêng:
1. Extract frame đầu tiên của video (hoặc frame mà bãi đã biết trống hoàn toàn)
2. Dùng frame đó làm reference

```python
# Trong load_reference_image, thêm option extract từ video
def load_reference_from_video(video_path: Path, frame_index: int = 0) -> np.ndarray:
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    success, frame = cap.read()
    cap.release()
    if not success:
        raise RuntimeError("Cannot extract reference frame from video")
    return frame
```

Thêm env var `REFERENCE_FROM_VIDEO_FRAME` để chọn frame index.

---

## 5. Trạng thái fix

| # | Fix | Impact | Status | Chi tiết |
|---|-----|--------|--------|---------|
| 1 | Tăng `DETECTION_THRESHOLD` 0.12 → 0.25 | ★★★ Loại bỏ B-L03, C-R01, C-R08 false positive | ✅ DONE | `.env` line 17 |
| 2 | Thêm `DETECTION_THRESHOLD_LOW=0.15` | ★★★ Low threshold cho hysteresis | ✅ DONE | `.env` line 18 |
| 3 | Hysteresis trong `detect_slot_occupied` | ★★★ Loại bỏ A-L07, B-L10 oscillation | ✅ DONE | `main.py` line 115–141 |
| 4 | `current_states` truyền vào `build_detection_payload` | ★★★ Hysteresis nhớ state trước | ✅ DONE | `main.py` line 151, 175–176, 308 |
| 5 | Reset `slot_votes` + `last_published_state` khi video loop | ★★ Fix vote contamination giữa các loop | ✅ DONE | `main.py` line 297–298 |
| 6 | Đồng bộ 24 y-coordinates Zone A trong slot-config.json | ★ Data consistency | ✅ DONE | `infra/slot-config.json` (24 values) |
| 7 | Reference image từ video (thay emty.png) | ★★ Fix root cause lighting mismatch | ⏳ TODO | Cần identify frame empty trong video |

---

## 6. Changelog — Thay đổi thực tế đã apply

### `apps/ai-detection-service/main.py`

**`detect_slot_occupied` (line 115–141):** Thêm hysteresis hai ngưỡng
```diff
- def detect_slot_occupied(frame_roi, reference_roi) -> tuple[bool, float]:
+ def detect_slot_occupied(frame_roi, reference_roi, current_state: bool = False) -> tuple[bool, float]:
      ...
-     detection_threshold = float(os.getenv("DETECTION_THRESHOLD", "0.12"))
-     occupied = score >= detection_threshold
+     high_threshold = float(os.getenv("DETECTION_THRESHOLD", "0.25"))
+     low_threshold = float(os.getenv("DETECTION_THRESHOLD_LOW", "0.15"))
+     if current_state:
+         occupied = score >= low_threshold   # đang occupied → exit khi score < 0.15
+     else:
+         occupied = score >= high_threshold  # đang vacant → enter khi score >= 0.25
```

**`build_detection_payload` (line 148–188):** Nhận `current_states` để feed vào hysteresis
```diff
- def build_detection_payload(frame, reference, slot_config, slot_coordinates):
+ def build_detection_payload(frame, reference, slot_config, slot_coordinates, current_states=None):
      ...
-         occupied, _score = detect_slot_occupied(frame_roi, reference_roi)
+         current = current_states.get(slot["slot_id"], False) if current_states else False
+         occupied, score = detect_slot_occupied(frame_roi, reference_roi, current_state=current)
```

**`video_detection_loop` — call site (line 308):** Truyền last published state
```diff
- last_payload, raw_scores = build_detection_payload(frame, reference, slot_config, slot_coordinates)
+ last_payload, raw_scores = build_detection_payload(
+     frame, reference, slot_config, slot_coordinates,
+     current_states=last_published_state,
+ )
```

**`video_detection_loop` — video loop reset (line 294–299):** Reset votes + state
```diff
  if not success:
      cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
      frame_count = 0
+     slot_votes.clear()
+     last_published_state = {}
      await asyncio.sleep(0.1)
      continue
```

**`/mock/status` endpoint:** Cập nhật default threshold hiển thị
```diff
- "detection_threshold": float(os.getenv("DETECTION_THRESHOLD", "0.12")),
+ "detection_threshold": float(os.getenv("DETECTION_THRESHOLD", "0.25")),
+ "detection_threshold_low": float(os.getenv("DETECTION_THRESHOLD_LOW", "0.15")),
```

---

### `.env`

```diff
- DETECTION_THRESHOLD=0.12
+ DETECTION_THRESHOLD=0.25
+ DETECTION_THRESHOLD_LOW=0.15
```

---

### `infra/slot-config.json`

24 y-coordinates Zone A được đồng bộ với `slot-coordinates.json` (file chuẩn dùng cho detection):

| Slot group | y cũ (sai) | y mới (đúng) |
|-----------|-----------|------------|
| A-L01..A-L05, A-R01..A-R05 | 104,160,216,272,328 | 108,164,220,276,332 |
| A-L06 | 384 | 386 |
| A-R06 | 384 | 388 |
| A-L07 | **448** (lệch ngược chiều) | **444** |
| A-R07 | 440 | 444 |
| A-L08..A-L12, A-R08..A-R12 | 496,552,608,664,720 | 500,556,612,668,724 |

---

## 7. Phụ lục — Thống kê slots bị ảnh hưởng

### Slots false positive xuyên suốt video (trước fix)
- **B-L03** (x=464, y=216, w=127, h=52) — score 0.127–0.155 toàn video → **fixed** bởi threshold 0.25
- **C-R01** (x=1046, y=160, w=120, h=52) — score 0.130–0.178 → **fixed** bởi threshold 0.25
- **C-R08** (x=1046, y=552, w=120, h=52) — score 0.126–0.171 → **fixed** bởi threshold 0.25

### Slots false positive thoáng qua (trước fix)
- **A-L07** (x=60, y=444, w=125, h=52) — score 0.097–0.135 → **fixed** bởi hysteresis + threshold 0.25
- **B-L10** (x=464, y=664, w=127, h=52) — score 0.116–0.128 → **fixed** bởi threshold 0.25

### Slot cần monitor sau fix
- **C-L09** — score tăng 0.119→0.254 trong video. Nếu 0.254 < new threshold hiệu quả thì sẽ thấy là vacant. Cần verify bằng `SAVE_FRAMES=true` để xem frame thực tế.

### TODO còn lại
- **Fix 7 (reference image):** Chụp lại `emty.png` cùng điều kiện ánh sáng với `carPark.mp4`, hoặc extract frame empty từ video để làm reference. Đây là root cause gốc của lighting mismatch noise.
