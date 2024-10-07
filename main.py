import os
import requests
from dotenv import load_dotenv  # Untuk memuat variabel dari file .env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Memuat variabel dari file .env
load_dotenv()

# Mengambil konfigurasi dari file .env dengan nilai default jika tidak ditemukan
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')  # Gunakan nilai default '' untuk mencegah None
WORDPRESS_API_URL = os.getenv('WORDPRESS_API_URL', '')  # Sama dengan di atas
WORDPRESS_USER = os.getenv('WORDPRESS_USER', '')  # Pastikan ini string
WORDPRESS_PASS = os.getenv('WORDPRESS_PASS', '')  # Pastikan ini string
RESULTS_PER_PAGE = int(os.getenv('RESULTS_PER_PAGE', 5))  # Default 5 jika tidak ditemukan

# Cache untuk menyimpan hasil pencarian sementara
search_cache = {}

# Fungsi untuk mencari artikel di WordPress
def search_wordpress(query):
    if query in search_cache:
        # Jika hasil pencarian sudah ada di cache, gunakan hasil cache
        return search_cache[query]
    
    try:
        # Pastikan bahwa semua variabel yang digunakan adalah string
        if WORDPRESS_USER and WORDPRESS_PASS:
            response = requests.get(WORDPRESS_API_URL,
                                    params={'search': query},
                                    auth=(WORDPRESS_USER, WORDPRESS_PASS))  # Auth tidak boleh None
        else:
            response = requests.get(WORDPRESS_API_URL,
                                    params={'search': query})  # Jika auth tidak tersedia

        if response.status_code == 200:
            posts = response.json()
            # Simpan hasil pencarian di cache
            search_cache[query] = posts
            return posts
        else:
            return None
    except Exception as e:
        return None

# Fungsi untuk membangun pesan hasil pencarian per halaman
def build_search_results(posts, page):
    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    paged_posts = posts[start:end]

    if not paged_posts:
        return "No more results."

    message = ""
    for post in paged_posts:
        title = post['title']['rendered']
        link = post['link']
        message += f"Data: {title}\nLink: {link}\n\n"
    return message

# Fungsi untuk membuat inline keyboard untuk navigasi halaman
def build_pagination_keyboard(query, current_page):
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton("Previous", callback_data=f"prev|{query}|{current_page-1}"))
    if (current_page + 1) * RESULTS_PER_PAGE < len(search_cache[query]):
        buttons.append(InlineKeyboardButton("Next", callback_data=f"next|{query}|{current_page+1}"))
    
    return InlineKeyboardMarkup([buttons])

# Fungsi untuk menangani pesan teks yang masuk
async def handle_message(update: Update, context):
    message = update.message
    if message and message.text:
        user_message = message.text
        posts = search_wordpress(user_message)

        if posts:
            # Mulai dari halaman pertama
            first_page_results = build_search_results(posts, 0)
            reply_markup = build_pagination_keyboard(user_message, 0)
            await message.reply_text(first_page_results, reply_markup=reply_markup)
        else:
            await message.reply_text("Tidak ditemukan.")
    else:
        # Jika tidak ada teks dalam pesan, mungkin ini adalah update lain yang tidak relevan
        return

# Fungsi untuk menangani navigasi halaman
async def handle_pagination(update: Update, context):
    query = update.callback_query
    if query and query.data:
        query_data = query.data.split('|')
        action = query_data[0]
        search_query = query_data[1]
        current_page = int(query_data[2])

        # Bangun hasil pencarian berdasarkan halaman
        if search_query in search_cache:
            posts = search_cache[search_query]
            page_results = build_search_results(posts, current_page)
            reply_markup = build_pagination_keyboard(search_query, current_page)
            await query.edit_message_text(page_results, reply_markup=reply_markup)
    else:
        # Jika query tidak valid, kita abaikan saja
        return

# Fungsi untuk memulai bot
async def start(update: Update, context):
    message = update.message
    if message:
        await message.reply_text("Selamat datang di database HARIAGUNG.COM, silahkan masukkan kata kunci untuk mencari data.")

def main():
    # Setup Application, pastikan TELEGRAM_TOKEN tidak None
    if TELEGRAM_TOKEN:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Command handler untuk perintah /start
        application.add_handler(CommandHandler("start", start))

        # Message handler untuk menangani pesan teks
        application.add_handler(MessageHandler(filters.TEXT, handle_message))

        # CallbackQuery handler untuk menangani pagination
        application.add_handler(CallbackQueryHandler(handle_pagination))

        # Menjalankan bot menggunakan run_polling
        application.run_polling()
    else:
        print("Telegram token tidak ditemukan. Pastikan .env diatur dengan benar.")

if __name__ == '__main__':
    main()
