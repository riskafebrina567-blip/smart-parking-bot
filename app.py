from flask import Flask, request, jsonify
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import logging
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

# --- KONFIGURASI ---
API_TOKEN = '8364529044:AAHP8IUmZ5JdiHk1Emk6d_eRKMNoH1GfqdQ'
WEBHOOK_URL = 'https://smart-parking-bot.onrender.com'  # Ganti dengan URL Render Anda
SENSOR_API_KEY = 'smartparking2024'

# Timeout booking dalam menit
BOOKING_TIMEOUT_MINUTES = 15

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- DATA PARKIR (GRID 4 Baris x 3 Kolom) ---
parking_grid = {}
rows = ['A', 'B', 'C', 'D']
cols = [1, 2, 3]

# Inisialisasi slot kosong saat server nyala
for r in rows:
    for c in cols:
        slot_id = f"{r}{c}"
        parking_grid[slot_id] = {
            "sensor": False,
            "booking": False,
            "booked_by": None,
            "booked_by_name": None,
            "booked_at": None
        }

# --- HELPER FUNCTIONS ---

def check_and_expire_bookings():
    """Cek dan expire booking yang sudah timeout"""
    now = datetime.now()
    expired_slots = []
    
    for slot_id, data in parking_grid.items():
        if data['booking'] and data['booked_at']:
            expiry_time = data['booked_at'] + timedelta(minutes=BOOKING_TIMEOUT_MINUTES)
            if now > expiry_time:
                parking_grid[slot_id]['booking'] = False
                parking_grid[slot_id]['booked_by'] = None
                parking_grid[slot_id]['booked_by_name'] = None
                parking_grid[slot_id]['booked_at'] = None
                expired_slots.append(slot_id)
                logger.info(f"Booking expired for slot {slot_id}")
    
    return expired_slots

def get_remaining_time(slot_id):
    """Hitung sisa waktu booking"""
    data = parking_grid[slot_id]
    if data['booking'] and data['booked_at']:
        expiry_time = data['booked_at'] + timedelta(minutes=BOOKING_TIMEOUT_MINUTES)
        remaining = expiry_time - datetime.now()
        if remaining.total_seconds() > 0:
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            return f"{minutes}m {seconds}s"
    return None

def require_api_key(f):
    """Decorator untuk validasi API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != SENSOR_API_KEY:
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- LOGIKA UTAMA ---

def generate_map():
    """Generate peta parkir dengan status terkini"""
    check_and_expire_bookings()
    
    map_text = "*🅿️ DENAH PARKIR (3x4)*\n"
    map_text += "━━━━━━━━━━━━━━━━━━\n\n"
    map_text += "     1️⃣  2️⃣  3️⃣\n"
    
    for r in rows:
        row_str = f" {r}  "
        for c in cols:
            slot_id = f"{r}{c}"
            data = parking_grid[slot_id]
            
            if data['sensor']:
                row_str += "🚗 "
            elif data['booking']:
                row_str += "🔒 "
            else:
                row_str += "🟢 "
        
        map_text += f"{row_str}\n"

    map_text += "\n━━━━━━━━━━━━━━━━━━\n"
    map_text += "🟢 Kosong | 🔒 Booked | 🚗 Terisi\n"
    map_text += f"⏱️ Timeout booking: {BOOKING_TIMEOUT_MINUTES} menit\n"
    map_text += "\n📝 *Perintah:*\n"
    map_text += "`/book ID` - Reservasi (cth: /book A1)\n"
    map_text += "`/cancel ID` - Batalkan reservasi\n"
    map_text += "`/status ID` - Cek status slot"
    
    return map_text

def get_slot_detail(slot_id):
    """Dapatkan detail status slot"""
    if slot_id not in parking_grid:
        return None
    
    data = parking_grid[slot_id]
    detail = f"*Detail Slot {slot_id}*\n\n"
    
    if data['sensor']:
        detail += "Status: 🚗 *Terisi* (ada kendaraan)\n"
    elif data['booking']:
        remaining = get_remaining_time(slot_id)
        detail += f"Status: 🔒 *Direservasi*\n"
        detail += f"Oleh: {data['booked_by_name'] or 'Unknown'}\n"
        if remaining:
            detail += f"Sisa waktu: {remaining}\n"
    else:
        detail += "Status: 🟢 *Tersedia*\n"
    
    return detail

# --- TELEGRAM HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    logger.info(f"User {message.from_user.id} ({message.from_user.first_name}) started bot")
    
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton('Cek Ketersediaan 🅿️')
    btn2 = KeyboardButton('Reservasi Parkir 🎫')
    btn3 = KeyboardButton('Booking Saya 📋')
    markup.add(btn1, btn2, btn3)
    
    welcome_msg = (
        "🚗 *Selamat datang di Smart Parking System!*\n\n"
        "Sistem ini membantu Anda mencari dan mereservasi slot parkir.\n\n"
        "*Fitur:*\n"
        "• Cek ketersediaan slot real-time\n"
        "• Reservasi slot parkir\n"
        f"• Auto-cancel setelah {BOOKING_TIMEOUT_MINUTES} menit\n\n"
        "Gunakan tombol di bawah atau ketik perintah manual."
    )
    
    bot.reply_to(message, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == 'Cek Ketersediaan 🅿️')
def check_parking(message):
    logger.info(f"User {message.from_user.id} checking availability")
    bot.reply_to(message, generate_map(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == 'Reservasi Parkir 🎫')
def booking_instruction(message):
    check_and_expire_bookings()
    
    empty_slots = [
        k for k, v in parking_grid.items() 
        if not v['sensor'] and not v['booking']
    ]
    
    msg = "🎫 *Reservasi Parkir*\n\n"
    msg += "Ketik perintah booking dengan format:\n"
    msg += "`/book [SLOT]`\n\n"
    msg += "Contoh: `/book C2`\n\n"
    
    if empty_slots:
        msg += f"✅ *Slot Tersedia ({len(empty_slots)}):*\n"
        msg += f"`{', '.join(sorted(empty_slots))}`"
    else:
        msg += "❌ *Semua slot penuh!*\n"
        msg += "Silakan coba lagi nanti."
    
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == 'Booking Saya 📋')
def my_bookings(message):
    user_id = message.from_user.id
    check_and_expire_bookings()
    
    my_slots = [
        slot_id for slot_id, data in parking_grid.items()
        if data['booked_by'] == user_id
    ]
    
    if my_slots:
        msg = "📋 *Booking Aktif Anda:*\n\n"
        for slot_id in my_slots:
            remaining = get_remaining_time(slot_id)
            msg += f"• Slot *{slot_id}*"
            if remaining:
                msg += f" (sisa: {remaining})"
            msg += "\n"
        msg += f"\nKetik `/cancel [SLOT]` untuk membatalkan."
    else:
        msg = "📋 Anda tidak memiliki booking aktif."
    
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['book'])
def book_slot(message):
    try:
        check_and_expire_bookings()
        
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(
                message, 
                "❌ Format salah!\n\nGunakan: `/book [SLOT]`\nContoh: `/book A1`",
                parse_mode="Markdown"
            )
            return
            
        slot_id = parts[1].upper()
        user_id = message.from_user.id
        user_name = message.from_user.first_name or "User"
        
        if slot_id not in parking_grid:
            valid_slots = ', '.join(sorted(parking_grid.keys()))
            bot.reply_to(
                message, 
                f"❌ Slot `{slot_id}` tidak valid!\n\nSlot yang tersedia: `{valid_slots}`",
                parse_mode="Markdown"
            )
            return
        
        existing_booking = [
            sid for sid, data in parking_grid.items()
            if data['booked_by'] == user_id
        ]
        
        if existing_booking:
            bot.reply_to(
                message,
                f"❌ Anda sudah memiliki booking aktif di slot `{existing_booking[0]}`.\n\n"
                f"Batalkan dulu dengan `/cancel {existing_booking[0]}` jika ingin pindah.",
                parse_mode="Markdown"
            )
            return
        
        data = parking_grid[slot_id]
        
        if data['sensor']:
            bot.reply_to(
                message, 
                f"❌ Gagal! Slot `{slot_id}` sedang ada kendaraan.",
                parse_mode="Markdown"
            )
        elif data['booking']:
            remaining = get_remaining_time(slot_id)
            msg = f"❌ Gagal! Slot `{slot_id}` sudah direservasi."
            if remaining:
                msg += f"\nSisa waktu: {remaining}"
            bot.reply_to(message, msg, parse_mode="Markdown")
        else:
            parking_grid[slot_id]['booking'] = True
            parking_grid[slot_id]['booked_by'] = user_id
            parking_grid[slot_id]['booked_by_name'] = user_name
            parking_grid[slot_id]['booked_at'] = datetime.now()
            
            logger.info(f"User {user_id} ({user_name}) booked slot {slot_id}")
            
            bot.reply_to(
                message, 
                f"✅ *Sukses!*\n\n"
                f"Slot `{slot_id}` berhasil direservasi untuk Anda.\n"
                f"⏱️ Booking berlaku selama *{BOOKING_TIMEOUT_MINUTES} menit*.\n\n"
                f"Segera parkir atau booking akan otomatis dibatalkan.",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Book error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan sistem. Silakan coba lagi.")

@bot.message_handler(commands=['cancel'])
def cancel_booking(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(
                message, 
                "❌ Format salah!\n\nGunakan: `/cancel [SLOT]`\nContoh: `/cancel A1`",
                parse_mode="Markdown"
            )
            return

        slot_id = parts[1].upper()
        user_id = message.from_user.id
        
        if slot_id not in parking_grid:
            bot.reply_to(
                message, 
                f"❌ Slot `{slot_id}` tidak valid!",
                parse_mode="Markdown"
            )
            return
        
        data = parking_grid[slot_id]
        
        if not data['booking']:
            bot.reply_to(
                message, 
                f"ℹ️ Slot `{slot_id}` tidak ada reservasi aktif.",
                parse_mode="Markdown"
            )
            return
        
        if data['booked_by'] != user_id:
            bot.reply_to(
                message, 
                f"❌ Anda tidak bisa membatalkan reservasi orang lain!",
                parse_mode="Markdown"
            )
            return
        
        parking_grid[slot_id]['booking'] = False
        parking_grid[slot_id]['booked_by'] = None
        parking_grid[slot_id]['booked_by_name'] = None
        parking_grid[slot_id]['booked_at'] = None
        
        logger.info(f"User {user_id} cancelled booking for slot {slot_id}")
        
        bot.reply_to(
            message, 
            f"✅ Reservasi slot `{slot_id}` berhasil dibatalkan.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan sistem. Silakan coba lagi.")

@bot.message_handler(commands=['status'])
def check_status(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(
                message, 
                "❌ Format salah!\n\nGunakan: `/status [SLOT]`\nContoh: `/status A1`",
                parse_mode="Markdown"
            )
            return
        
        slot_id = parts[1].upper()
        check_and_expire_bookings()
        
        detail = get_slot_detail(slot_id)
        if detail:
            bot.reply_to(message, detail, parse_mode="Markdown")
        else:
            bot.reply_to(
                message, 
                f"❌ Slot `{slot_id}` tidak valid!",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Status error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan sistem.")

# --- FLASK ROUTES ---

@app.route('/')
def home():
    check_and_expire_bookings()
    
    total_slots = len(parking_grid)
    occupied = sum(1 for v in parking_grid.values() if v['sensor'])
    booked = sum(1 for v in parking_grid.values() if v['booking'] and not v['sensor'])
    available = total_slots - occupied - booked
    
    return jsonify({
        "status": "running",
        "service": "Smart Parking System",
        "statistics": {
            "total_slots": total_slots,
            "occupied": occupied,
            "booked": booked,
            "available": available
        }
    })

@app.route('/slots', methods=['GET'])
def get_all_slots():
    check_and_expire_bookings()
    
    slots_data = {}
    for slot_id, data in parking_grid.items():
        slots_data[slot_id] = {
            "occupied": data['sensor'],
            "booked": data['booking'],
            "available": not data['sensor'] and not data['booking']
        }
    
    return jsonify(slots_data)

# Webhook Telegram
@app.route('/' + API_TOKEN, methods=['POST'])
def getMessage():
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

# Setup Webhook
@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(0.5)
        
        webhook_url = f"{WEBHOOK_URL}/{API_TOKEN}"
        success = bot.set_webhook(url=webhook_url)
        
        if success:
            logger.info(f"Webhook set successfully to {webhook_url}")
            return jsonify({
                "status": "success",
                "message": "Webhook setup successful",
                "webhook_url": webhook_url
            })
        else:
            return jsonify({
                "status": "failed",
                "message": "Webhook setup failed"
            }), 500
            
    except Exception as e:
        logger.error(f"Set webhook error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/remove_webhook', methods=['GET', 'POST'])
def remove_webhook():
    try:
        bot.remove_webhook()
        return jsonify({"status": "success", "message": "Webhook removed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Sensor Update dari Wokwi
@app.route('/update_sensor', methods=['POST'])
@require_api_key
def update_sensor():
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "no data provided"}), 400
        
        slot_id = data.get('slot_id', '').upper()
        occupied = data.get('occupied')
        
        if not slot_id:
            return jsonify({"error": "slot_id required"}), 400
        
        if occupied is None:
            return jsonify({"error": "occupied status required"}), 400
        
        if slot_id not in parking_grid:
            return jsonify({"error": f"invalid slot: {slot_id}"}), 400
        
        old_status = parking_grid[slot_id]['sensor']
        
        if old_status != occupied:
            parking_grid[slot_id]['sensor'] = occupied
            logger.info(f"Sensor update: {slot_id} = {'occupied' if occupied else 'empty'}")
            
            if occupied and parking_grid[slot_id]['booking']:
                parking_grid[slot_id]['booking'] = False
                parking_grid[slot_id]['booked_by'] = None
                parking_grid[slot_id]['booked_by_name'] = None
                parking_grid[slot_id]['booked_at'] = None
                logger.info(f"Booking cleared for {slot_id} - car arrived")
        
        return jsonify({
            "status": "updated",
            "slot_id": slot_id,
            "occupied": occupied
        }), 200
        
    except Exception as e:
        logger.error(f"Sensor update error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_sensors', methods=['POST'])
@require_api_key
def update_sensors():
    try:
        data = request.json
        
        if not data or 'sensors' not in data:
            return jsonify({"error": "sensors array required"}), 400
        
        results = []
        for sensor in data['sensors']:
            slot_id = sensor.get('slot_id', '').upper()
            occupied = sensor.get('occupied')
            
            if slot_id in parking_grid and occupied is not None:
                old_status = parking_grid[slot_id]['sensor']
                if old_status != occupied:
                    parking_grid[slot_id]['sensor'] = occupied
                    
                    if occupied and parking_grid[slot_id]['booking']:
                        parking_grid[slot_id]['booking'] = False
                        parking_grid[slot_id]['booked_by'] = None
                        parking_grid[slot_id]['booked_by_name'] = None
                        parking_grid[slot_id]['booked_at'] = None
                
                results.append({"slot_id": slot_id, "status": "updated"})
            else:
                results.append({"slot_id": slot_id, "status": "invalid"})
        
        return jsonify({"results": results}), 200
        
    except Exception as e:
        logger.error(f"Batch sensor update error: {e}")
        return jsonify({"error": str(e)}), 500

# Health check untuk Render
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

# Ping endpoint untuk keep-alive
@app.route('/ping', methods=['GET'])
def ping():
    return "pong", 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
