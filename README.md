# **Auto Answer Timer (Adaptive & Gamified)**

This add-on automatically reveals the answer after a set time, forcing you to think faster. It features an **adaptive timer** that learns your speed for each card and turns your reviews into a game where you try to beat your own records.

Perfect for **speed-reviewing**, **blitz sessions**, or **hands-free studying**.

---

## 🚀 Key Features

- **🧠 Adaptive Timer**: Automatically sets a custom timer for each card based on your first correct answer speed.
- **🎮 Gamification**: Try to beat your previous time! The add-on challenges you to answer faster than before.
- **📉 Smart Adjustments**:
    - **Streaks**: Answer correctly 2 times in a row? The timer gets **1 second shorter**, pushing you to be faster.
    - **Struggles**: Get it wrong 2 times in a row? The timer gets **1 second longer**, giving you more breathing room.
- **⚡ Auto-Update**: If you answer correctly *faster* than your current record, the timer updates to your new speed.
- **🔧 Manual Override**: Set a specific time for any card if you want fixed control.

---

## 📝 How It Works

1. **First Review**: The first time you review a card, there is no timer. Answer correctly, and that time becomes your **baseline**.
2. **Subsequent Reviews**: The answer will auto-reveal based on your baseline.
3. **The Challenge**: An overlay in the top-right shows your target time vs. your current time.
    - *Example*: "1.2s / 3.5s" (You took 1.2s, the limit was 3.5s).
4. **Progression**:
    - **Be right 1+ times**: Timer reduces by **1000ms (1s)**.
    - **Get it wrong 1+ times**: Timer increases by **1000ms (1s)**.
    - **New Record**: If you beat the timer, that becomes the new limit.

---

## ⚙️ Controls

### Toggle On/Off
**Tools → Toggle Per-Card Auto Answer**

### Manual Timer Setting
Right-click during review (or use the "More" menu) and select:
**Set Auto-Answer Timer for This Card**
- Enter a number (e.g., `5`) to set a fixed 5-second timer.
- Enter `0` to disable the timer for that specific card.

---

## ⚠️ Notes

- The add-on does *not* auto-advance to the next card (only auto-reveals).
- Works during normal reviews.