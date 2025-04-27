import hashlib
import random
import csv
import numpy as np
from scipy.stats import kurtosis, skew
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import datetime
import os

# Hàm kiểm tra MD5 hợp lệ
def is_valid_md5(md5):
    return len(md5) == 32 and all(c in '0123456789abcdefABCDEF' for c in md5)

# Tính entropy (mức độ ngẫu nhiên)
def calculate_entropy(values):
    _, counts = np.unique(values, return_counts=True)
    prob = counts / len(values)
    return -np.sum(prob * np.log2(prob))

# Tính skewness (độ lệch)
def calculate_skewness(values):
    return skew(values)

# Tính kurtosis (độ nhọn)
def calculate_kurtosis(values):
    return kurtosis(values)

# Tính điểm thông minh với Skewness và Kurtosis
def calculate_smart_score(entropy, stddev, gradient, hex_density, repetition_penalty, bias_rolling, skewness, kurtosis):
    score = 0
    if entropy > 0.58:
        score += 2
    if stddev > 55:
        score += 1
    if bias_rolling < 0.2:
        score += 1
    if repetition_penalty < 0.1:
        score += 1
    if gradient > 80:
        score += 1
    if hex_density > 0.55:
        score += 1
    if skewness > 0.5:
        score += 1
    if kurtosis > 3:
        score += 1
    return score

# Tính xác suất dựa trên điểm thông minh
def calculate_probability(smart_score):
    probabilities = {
        8: 0.95,
        7: 0.85,
        6: 0.75,
        5: 0.65,
        4: 0.55,
        3: 0.45
    }
    return probabilities.get(smart_score, 0.45)

# Mô phỏng xúc xắc
def simulate_dice(result):
    min_total = 11 if result == "Tài" else 3
    max_total = 18 if result == "Tài" else 10
    while True:
        d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2 + d3
        if min_total <= total <= max_total:
            return d1, d2, d3, total

# Chuyển đổi số xúc xắc thành emoji
def get_dice_emoji(num):
    dice_emojis = {
        1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"
    }
    return dice_emojis.get(num, "🎲")

# Phân tích MD5 và dự đoán
def analyze_md5(md5):
    # Chuyển MD5 thành mảng các số byte
    bytes = [int(md5[i:i+2], 16) for i in range(0, len(md5), 2)]
    
    avg = np.mean(bytes)
    stddev = np.std(bytes)
    gradient = np.sum(np.abs(np.diff(bytes)))
    
    # Hex density
    hex_density = sum(1 for b in bytes if b >= 8) / len(bytes)
    
    # Tính entropy
    entropy = calculate_entropy(bytes)
    
    # Lặp lại penalty
    repetition_penalty = 1 - len(set(bytes)) / len(bytes)
    if repetition_penalty < 0:
        repetition_penalty = 0
    
    # Bias rolling (độ lệch giữa các byte liên tiếp)
    bias_rolling = np.mean(np.abs(np.diff(bytes)))
    
    # Tính skewness và kurtosis
    skewness = calculate_skewness(bytes)
    kurtosis_value = calculate_kurtosis(bytes)
    
    # Tính điểm CRC16
    crc = crc16(bytes)
    
    # Tính điểm thông minh
    smart_score = calculate_smart_score(entropy, stddev, gradient, hex_density, repetition_penalty, bias_rolling, skewness, kurtosis_value)
    
    # Tính xác suất
    prob = calculate_probability(smart_score)
    
    # Dự đoán Tài/Xỉu
    result = "Tài" if prob >= 0.5 else "Xỉu"
    
    # Đánh giá độ tin cậy
    confidence = "Very High 🔥" if prob >= 0.9 else ("High 💪" if prob >= 0.8 else ("Medium 🧠" if prob >= 0.7 else "Low 🫣"))
    
    method_used = f"Entropy={entropy:.3f} | StdDev={stddev:.1f} | Bias={bias_rolling:.2f} | Gradient={gradient} | HexDensity={hex_density:.2f} | Skewness={skewness:.2f} | Kurtosis={kurtosis_value:.2f} | CRC16={crc} | Score={smart_score}"

    return result, prob, confidence, method_used

# Tính CRC16
def crc16(bytes):
    crc = 0xFFFF
    for b in bytes:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
    return crc & 0xFFFF

# Lưu lịch sử vào file CSV
def save_history(md5, result, probability, confidence, method_used):
    history_file = "history.csv"
    header = ["Time", "MD5", "Result", "Probability", "Confidence", "Details"]
    
    data = {
        "Time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "MD5": md5,
        "Result": result,
        "Probability": f"{probability*100:.1f}%",
        "Confidence": confidence,
        "Details": method_used
    }
    
    file_exists = os.path.exists(history_file)
    
    with open(history_file, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# Hàm xử lý tin nhắn từ người dùng
async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    chat_id = update.message.chat.id
    
    if not is_valid_md5(text):
        await update.message.reply_text("⚠️ Lỗi: Chuỗi gửi không phải MD5 hợp lệ. Vui lòng gửi chuỗi MD5 gồm 32 ký tự hex (0-9, a-f).")
        return
    
    result, prob, confidence, method_used = analyze_md5(text)
    
    d1, d2, d3, total = simulate_dice(result)
    
    message = f"""
🎯 <b>Dự đoán Tài/Xỉu từ MD5</b>

🔐 <b>MD5:</b> <code>{text}</code>

🎲 <b>Xúc xắc:</b> {d1}, {d2}, {d3} → <b>Tổng:</b> {total}
🎰 <b>Mô phỏng xúc xắc:</b> {get_dice_emoji(d1)} {get_dice_emoji(d2)} {get_dice_emoji(d3)}

📈 <b>Dự đoán:</b> {result}
🏷️ <b>Độ tin cậy:</b> {confidence} ({prob*100:.1f}%)

⚙️ <b>Phân tích thêm:</b> {method_used}

🕰️ <i>{datetime.datetime.utcnow().strftime('%H:%M:%S dd/MM/yyyy')}</i>
"""

    await update.message.reply_text(message, parse_mode="HTML")
    save_history(text, result, prob, confidence, method_used)

def main():
    application = Application.builder().token("7287917776:AAFKd8x1WY1JfnmG0POE4gm-iFAL28ir9FY").build()

    # Thêm handler cho các tin nhắn văn bản
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
