import os
import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
WORDPRESS_API_URL = os.getenv('WORDPRESS_API_URL', '')
WORDPRESS_USER = os.getenv('WORDPRESS_USER', '')
WORDPRESS_PASS = os.getenv('WORDPRESS_PASS', '')
RESULTS_PER_PAGE = int(os.getenv('RESULTS_PER_PAGE', 5))

search_cache = {}

def search_wordpress(query):
    if query in search_cache:
        return search_cache[query]
    
    try:
        if WORDPRESS_USER and WORDPRESS_PASS:
            response = requests.get(WORDPRESS_API_URL,
                                    params={'search': query},
                                    auth=(WORDPRESS_USER, WORDPRESS_PASS))
        else:
            response = requests.get(WORDPRESS_API_URL,
                                    params={'search': query})

        if response.status_code == 200:
            posts = response.json()
            search_cache[query] = posts
            return posts
        else:
            return None
    except Exception as e:
        return None

def build_search_results(posts, page):
    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    paged_posts = posts[start:end]

    if not paged_posts:
        return "❌ Tidak ada hasil lain."

    message = "🔍 Hasil Pencarian:\n\n"
    for i, post in enumerate(paged_posts, start=start+1):
        title = post['title']['rendered']
        link = post['link']
        message += f"📎 *Data #{i}*\n"
        message += f"━━━━━━━━━━━━━━━\n"
        message += f"📌 *Judul:* {title}\n"
        message += f"🔗 *Link:* {link}\n"
        message += f"━━━━━━━━━━━━━━━\n\n"
    
    total_results = len(posts)
    current_page = page + 1
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    
    message += f"📊 Halaman {current_page} dari {total_pages}\n"
    message += f"📝 Total data: {total_results}"
    
    return message

def build_pagination_keyboard(query, current_page):
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Sebelumnya", callback_data=f"prev|{query}|{current_page-1}"))
    if (current_page + 1) * RESULTS_PER_PAGE < len(search_cache[query]):
        buttons.append(InlineKeyboardButton("Selanjutnya ➡️", callback_data=f"next|{query}|{current_page+1}"))
    
    return InlineKeyboardMarkup([buttons])

async def handle_message(update: Update, context):
    message = update.message
    if message and message.text:
        search_query = message.text
        await message.reply_text("🔍 Sedang mencari...")
        
        posts = search_wordpress(search_query)

        if posts:
            first_page_results = build_search_results(posts, 0)
            reply_markup = build_pagination_keyboard(search_query, 0)
            await message.reply_text(first_page_results, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await message.reply_text("❌ Data tidak ditemukan.")
    else:
        return

async def handle_pagination(update: Update, context):
    query = update.callback_query
    if query and query.data:
        query_data = query.data.split('|')
        action = query_data[0]
        search_query = query_data[1]
        current_page = int(query_data[2])

        if search_query in search_cache:
            posts = search_cache[search_query]
            page_results = build_search_results(posts, current_page)
            reply_markup = build_pagination_keyboard(search_query, current_page)
            await query.edit_message_text(page_results, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        return

async def start(update: Update, context):
    message = update.message
    if message:
        welcome_text = """
🌟 *Selamat datang di Database HARIAGUNG.COM* 🌟

Silakan masukkan kata kunci untuk mencari data.

📝 *Petunjuk Penggunaan:*
• Ketik kata kunci atau nomor
• Gunakan tombol navigasi untuk melihat hasil lainnya
• Data ditampilkan 5 per halaman

🔍 *Mulai pencarian sekarang!*
        """
        await message.reply_text(welcome_text, parse_mode='Markdown')

def main():
    if TELEGRAM_TOKEN:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT, handle_message))
        application.add_handler(CallbackQueryHandler(handle_pagination))
        application.run_polling()
    else:
        print("❌ Telegram token tidak ditemukan. Pastikan .env diatur dengan benar.")

if __name__ == '__main__':
    main()
