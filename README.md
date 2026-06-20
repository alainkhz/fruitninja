# OpenCV Fruit Ninja

用 `OpenCV + MediaPipe + Pygame` 做的鏡頭版 Fruit Ninja。  
玩家不需要滑鼠，直接用鏡頭偵測食指移動來切水果。

目前專案已經完成可玩的單機版本，包含主選單、手指懸停操作、特殊水果、技能、關卡系統、歷史紀錄與音效。

## 目前功能

- 鏡頭偵測食指當作刀鋒
- 主選單支援手指懸停選擇
- 水果、炸彈、切中粒子效果
- 特殊水果
  - 金色水果：高分
  - 冰凍水果：暫時減速
  - 火焰水果：短時間分數 x2
  - 電擊水果：連鎖切附近水果
- 技能系統
  - 刀鋒衝刺：嚴格手勢觸發，短時間擴大切割判定
  - 旋風斬：清掉全畫面水果，不會切到炸彈
- 關卡系統
  - 達到指定分數升關
  - 關卡越高，生成與節奏會加快
  - 升關有過場提示與主題色變化
- 本地歷史紀錄
  - 分數
  - 最高關卡
  - 連擊
  - 水果數量
  - 結束原因
- 音效開關、鏡像開關、懸停速度設定

## 操作方式

- 把手伸到鏡頭前，移動食指切水果
- 手指停在按鈕上方一小段時間可選單操作
- 快速橫向揮動可觸發 `刀鋒衝刺`
- 畫圈手勢可觸發 `旋風斬`

鍵盤快捷鍵：

- `Esc` / `q`：離開遊戲
- `Space`：直接開始新局
- `m`：回主選單
- `h`：打開歷史紀錄
- `r`：在結算畫面重開
- `t`：播放測試音效

## 關卡規則

- 第 1 關目標分數：`600`
- 每升一關，下一關需求額外增加 `450`
- 關卡越高時，難度會同時提升：
  - 水果飛行速度更快
  - 生成間隔更短
  - 同時存在的水果數量更多

也就是：

- 第 1 關 -> 第 2 關：`600`
- 第 2 關 -> 第 3 關：`1050`
- 第 3 關 -> 第 4 關：`1500`

## 安裝

建議使用 Python 3.10 以上。

```bash
pip install -r requirements.txt
```

## 執行

```bash
python main.py
```

如果你是用 Codex runtime 跑，也可以直接：

```powershell
C:\Users\khzzi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe main.py
```

## 依賴

- `opencv-python`
- `mediapipe`
- `numpy`
- `pygame`

## 專案結構

- [main.py](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/main.py)
  - 主遊戲迴圈、碰撞、技能、關卡、選單切換
- [tracking/](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/tracking)
  - 手部與食指追蹤
- [camera/](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/camera)
  - 攝影機開啟與後端 fallback
- [game/](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/game)
  - 狀態、物件、生成器、歷史紀錄、設定、音效、選單
- [render/](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/render)
  - HUD、畫面特效、選單與結算畫面
- [outputs/](C:/Users/khzzi/Documents/Codex/2026-06-18/opencv-fruit-ninja-md/outputs)
  - 設計文件與 roadmap

## 已知事項

- 不同 Windows 裝置的攝影機後端表現不同，所以專案內有自動 fallback。
- `MediaPipe` 第一次啟動時可能會印出一些模型或 delegate 訊息，通常不是錯誤。
- 若鏡頭畫面偏黑、偏慢或抓不到手，先檢查光線與背景雜訊。

## 後續可擴充

- 真正的 Boss 關卡
- 關卡專屬背景主題與粒子風格
- 商店 / 升級 / 永久成長
- 更多技能與特殊水果互動
- 更完整的 UI 美術素材
