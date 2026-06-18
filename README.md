# OpenCV Fruit Ninja

用 `OpenCV + MediaPipe + Pygame` 做的鏡頭版 Fruit Ninja。  
玩家不是用滑鼠，而是直接用鏡頭偵測食指來操作，靠揮動手指切水果、觸發技能、躲炸彈。

## 功能特色

- 鏡頭手指追蹤操作
- 中文主選單與懸停選擇
- 多種水果與炸彈
- 特殊水果效果
  - 金色水果：高分
  - 冰凍水果：全場減速
  - 火焰水果：短時間分數 x2
  - 電擊水果：連鎖切水果
- Combo、分數浮字、粒子特效、切中效果
- 技能系統
  - 刀鋒衝刺
  - 旋風斬
- 歷史紀錄
- 任務結算
- 音效支援

## 操作方式

- 把手放到鏡頭前，讓系統抓到食指
- 快速揮動食指去切水果
- 手指停在按鈕上方一段時間可選擇選單
- `Esc` 或 `q`：離開
- `Space`：直接開始新局
- `m`：回主選單
- `h`：開歷史紀錄

## 技能說明

### 刀鋒衝刺

- 技能條要滿
- 需要更明確的橫向快速手勢才會觸發
- 觸發後短時間切割範圍會變大，畫面也會有明顯特效

### 旋風斬

- 技能條至少約 75%
- 用手指畫接近圓形的軌跡觸發
- 會瞬間切掉手指附近一圈水果

## 任務系統

目前每局會判定一些挑戰，例如：

- 單局達成 8 連擊
- 切到 2 顆金色水果
- 觸發火焰水果
- 觸發電擊連鎖
- 單局漏接不超過 1 次

## 安裝方式

建議使用 Python 3.10+。

```bash
pip install -r requirements.txt
```

## 執行方式

```bash
python main.py
```

## 專案依賴

- `opencv-python`
- `mediapipe`
- `numpy`
- `pygame`

## 目錄說明

- [`main.py`](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/main.py)：主遊戲流程
- [`tracking/`](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/tracking)：手部追蹤
- [`game/`](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/game)：物件、生成、狀態、音效、任務、紀錄
- [`render/`](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/render)：畫面渲染
- [`work/models/`](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/work/models)：手勢模型
- [`work/sounds/`](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/work/sounds)：遊戲音效
- [`outputs/`](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/outputs)：設計文件與 roadmap

## 注意事項

- 需要可用的攝影機
- 第一次執行時請確認鏡頭權限
- 若 `MediaPipe` 或 `pygame` 沒安裝成功，程式會無法啟動
- 若鏡頭解析度較低，手勢辨識穩定度會受光線與背景影響

## 後續可擴充方向

- 更多技能與 Boss 關卡
- 解鎖系統 / 星星系統
- 正式教學模式
- 更完整的視覺特效與 UI 動畫
