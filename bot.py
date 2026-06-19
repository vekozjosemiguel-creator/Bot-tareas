import telebot
import random
import requests
import json
import sqlite3
from datetime import datetime

# ========== CONFIGURACIÓN ==========
TOKEN = "8037309678:AAHgcOzlfF_3g1BBD_8RkMNpDgEgLLVV9vc"
ADSGRAM_TOKEN = "757fcee3c4fc4425acaeed9044fd1669"
BLOCK_ID = "35673"

bot = telebot.TeleBot(TOKEN)

# ========== BASE DE DATOS ==========
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance REAL DEFAULT 0,
    referred_by INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    last_daily DATETIME
)
''')
conn.commit()

# ========== FUNCIONES ==========
def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def create_user(user_id, username, first_name, referred_by=0):
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, referred_by)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, referred_by))
    conn.commit()

def update_balance(user_id, amount):
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

def get_balance(user_id):
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

# ========== COMANDOS ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "sin_username"
    first_name = message.from_user.first_name or "Usuario"

    referred_by = 0
    if len(message.text.split()) > 1:
        try:
            referred_by = int(message.text.split()[1])
            if referred_by == user_id:
                referred_by = 0
        except:
            referred_by = 0

    if not get_user(user_id):
        create_user(user_id, username, first_name, referred_by)
        update_balance(user_id, 0.05)
        bot.reply_to(message, f"🎉 ¡Bienvenido {first_name}!\nHas recibido 0.05 USDT de regalo.")
        
        if referred_by:
            update_balance(referred_by, 0.10)
            try:
                bot.send_message(referred_by, f"🎉 ¡Alguien se unió por tu enlace!\nHas ganado +0.10 USDT")
            except:
                pass
    else:
        bot.reply_to(message, f"👋 ¡Bienvenido de vuelta, {first_name}!")

    show_menu(message)

def show_menu(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    txt = f"""
🏆 *RICH TASK - Gana USDT*

💰 *Saldo:* {balance:.3f} USDT

📌 *Comandos:*
/ver - Ver anuncios y ganar
/referidos - Invitar amigos
/saldo - Ver tu saldo
/retirar - Retirar ganancias
/ayuda - Ayuda

🚀 *Invita amigos y gana 0.10 USDT por cada uno!*
"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📺 Ver anuncio", callback_data="ver"))
    markup.add(telebot.types.InlineKeyboardButton("📤 Invitar amigos", callback_data="invitar"))
    
    bot.reply_to(message, txt, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['ver'])
def ver_anuncio(message):
    user_id = message.from_user.id
    if not get_user(user_id):
        bot.reply_to(message, "Usa /start primero.")
        return
    
    try:
        url = "https://api.adsgram.ai/api/v1/ads"
        params = {
            "tgid": user_id,
            "blockid": BLOCK_ID,
            "language": "es",
            "token": ADSGRAM_TOKEN
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if not data.get('text_html'):
            bot.reply_to(message, "📺 No hay anuncios disponibles ahora. Intenta más tarde.")
            return
        
        text_html = data.get('text_html', '')
        image_url = data.get('image_url')
        click_url = data.get('click_url')
        reward_url = data.get('reward_url')
        button_name = data.get('button_name', 'Ver anuncio')
        button_reward_name = data.get('button_reward_name', 'Reclamar recompensa')
        
        markup = telebot.types.InlineKeyboardMarkup()
        btn_click = telebot.types.InlineKeyboardButton(button_name, url=click_url)
        btn_reward = telebot.types.InlineKeyboardButton(button_reward_name, callback_data=f"reward_{reward_url}")
        markup.add(btn_click, btn_reward)
        
        if image_url:
            bot.send_photo(user_id, image_url, caption=text_html, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(user_id, text_html, reply_markup=markup, parse_mode='HTML')
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error al cargar el anuncio. Intenta de nuevo.")

@bot.message_handler(commands=['referidos'])
def referidos(message):
    user_id = message.from_user.id
    if not get_user(user_id):
        bot.reply_to(message, "Usa /start primero.")
        return
    
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    txt = f"""
📤 *Tus referidos*

🔗 *Tu enlace de invitación:*
`{link}`

🎁 *Gana 0.10 USDT por cada amigo que se registre!*
"""
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.message_handler(commands=['saldo'])
def saldo(message):
    user_id = message.from_user.id
    if not get_user(user_id):
        bot.reply_to(message, "Usa /start primero.")
        return
    bot.reply_to(message, f"💰 Tu saldo: {get_balance(user_id):.3f} USDT")

@bot.message_handler(commands=['retirar'])
def retirar(message):
    user_id = message.from_user.id
    if not get_user(user_id):
        bot.reply_to(message, "Usa /start primero.")
        return
    balance = get_balance(user_id)
    if balance < 0.50:
        bot.reply_to(message, f"⚠️ Mínimo para retirar: 0.50 USDT\nTu saldo: {balance:.3f} USDT")
        return
    bot.reply_to(message, f"💳 *Solicitud de retiro*\nMonto: {balance:.3f} USDT\n\nEnvía tu dirección USDT (BEP20/TRC20) para procesar el retiro.", parse_mode='Markdown')

@bot.message_handler(commands=['ayuda'])
def ayuda(message):
    txt = """
📋 *COMANDOS DISPONIBLES*

/start - Iniciar el bot
/ver - Ver anuncios y ganar USDT
/referidos - Invitar amigos
/saldo - Ver tu saldo
/retirar - Retirar ganancias
/ayuda - Ayuda

🎁 *Bonos activos:*
• Bienvenida: 0.05 USDT
• Referido: 0.10 USDT
"""
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    
    if call.data == "ver":
        try:
            url = "https://api.adsgram.ai/api/v1/ads"
            params = {
                "tgid": user_id,
                "blockid": BLOCK_ID,
                "language": "es",
                "token": ADSGRAM_TOKEN
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if not data.get('text_html'):
                bot.answer_callback_query(call.id, "No hay anuncios ahora.")
                return
            
            text_html = data.get('text_html', '')
            image_url = data.get('image_url')
            click_url = data.get('click_url')
            reward_url = data.get('reward_url')
            button_name = data.get('button_name', 'Ver anuncio')
            button_reward_name = data.get('button_reward_name', 'Reclamar recompensa')
            
            markup = telebot.types.InlineKeyboardMarkup()
            btn_click = telebot.types.InlineKeyboardButton(button_name, url=click_url)
            btn_reward = telebot.types.InlineKeyboardButton(button_reward_name, callback_data=f"reward_{reward_url}")
            markup.add(btn_click, btn_reward)
            
            if image_url:
                bot.send_photo(user_id, image_url, caption=text_html, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_message(user_id, text_html, reply_markup=markup, parse_mode='HTML')
                
        except Exception as e:
            bot.answer_callback_query(call.id, "Error al cargar anuncio.")
    
    elif call.data == "invitar":
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.answer_callback_query(call.id, "📤 Enlace copiado!")
        bot.edit_message_text(f"🔗 *Tu enlace:*\n`{link}`\n\n🎁 Gana 0.10 USDT por cada amigo!", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='Markdown')
    
    elif call.data.startswith("reward_"):
        reward_url = call.data.replace("reward_", "")
        try:
            requests.get(reward_url, timeout=5)
            ganancia = round(random.uniform(0.02, 0.08), 3)
            update_balance(user_id, ganancia)
            bot.answer_callback_query(call.id, f"✅ Recompensa de +{ganancia} USDT reclamada!")
            bot.edit_message_text(f"✅ Recompensa de +{ganancia} USDT acreditada.\n💰 Saldo: {get_balance(user_id):.3f} USDT", 
                                  chat_id=call.message.chat.id, message_id=call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "❌ Error al reclamar recompensa.")

print("🤖 Bot de Tareas con AdsGram activo")
bot.infinity_polling()
