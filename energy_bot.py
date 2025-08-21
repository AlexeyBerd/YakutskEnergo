import requests
from bs4 import BeautifulSoup
import datetime
import time
import sys
import urllib3
import re
import json
import os
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('energy_bot.log')
    ]
)

# Отключаем предупреждения о SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- НАСТРОЙКИ ---
MAIN_URL = 'https://www.yakutskenergo.ru/press/news/news-remont/'
CHECK_TIMES = ["09:30", "17:30"]
TELEGRAM_BOT_TOKEN = '7501069858:AAG4I7n-Tmr9-DiLEAza8rTecKJdfcgaDe4'
USER_DATA_FILE = 'user_addresses.json'
USER_STATES_FILE = 'user_states.json'
CACHE_FILE = 'last_results.json'
LAST_CHECK_FILE = 'last_check_time.json'

# Переменная для хранения последнего update_id
last_update_id = 0

def load_user_data():
    """Загружает данные пользователей из файла"""
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки user_data: {e}")
            return {}
    return {}

def save_user_data(data):
    """Сохраняет данные пользователей в файл"""
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения user_data: {e}")

def load_user_states():
    """Загружает состояния пользователей"""
    if os.path.exists(USER_STATES_FILE):
        try:
            with open(USER_STATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки user_states: {e}")
            return {}
    return {}

def save_user_states(data):
    """Сохраняет состояния пользователей"""
    try:
        with open(USER_STATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения user_states: {e}")

def load_cache():
    """Загружает кэш последних результатов"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки cache: {e}")
            return {}
    return {}

def save_cache(cache_data):
    """Сохраняет кэш результатов"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения cache: {e}")

def load_last_check_time():
    """Загружает время последней проверки"""
    if os.path.exists(LAST_CHECK_FILE):
        try:
            with open(LAST_CHECK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки last_check: {e}")
            return {}
    return {}

def save_last_check_time(check_time):
    """Сохраняет время последней проверки"""
    try:
        with open(LAST_CHECK_FILE, 'w', encoding='utf-8') as f:
            json.dump(check_time, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения last_check: {e}")

def get_user_addresses(chat_id):
    """Получает адреса пользователя"""
    user_data = load_user_data()
    return user_data.get(str(chat_id), [])

def set_user_addresses(chat_id, addresses):
    """Устанавливает адреса пользователя"""
    user_data = load_user_data()
    user_data[str(chat_id)] = addresses
    save_user_data(user_data)

def get_user_state(chat_id):
    """Получает состояние пользователя"""
    states = load_user_states()
    return states.get(str(chat_id), 'idle')

def set_user_state(chat_id, state):
    """Устанавливает состояние пользователя"""
    states = load_user_states()
    states[str(chat_id)] = state
    save_user_states(states)

def send_telegram_message(chat_id, message, reply_markup=None):
    """Отправляет сообщение в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
            
        response = requests.post(url, data=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logging.error(f"❌ Ошибка отправки в Telegram: {e}")
        return False

def create_main_keyboard():
    """Создает основную клавиатуру с командами"""
    keyboard = {
        'keyboard': [
            ['📋 Мои адреса', '➕ Добавить адрес'],
            ['❌ Удалить адрес', '🗑️ Очистить все'],
            ['🔍 Проверить сейчас', '📊 Статус'],
            ['ℹ️ Помощь']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }
    return json.dumps(keyboard)

def create_cancel_keyboard():
    """Создает клавиатуру с отменой"""
    keyboard = {
        'keyboard': [
            ['❌ Отмена']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }
    return json.dumps(keyboard)

def create_remove_keyboard(addresses):
    """Создает клавиатуру для удаления адресов"""
    buttons = []
    for address in addresses:
        buttons.append([f'❌ {address}'])
    buttons.append(['❌ Отмена'])
    
    keyboard = {
        'keyboard': buttons,
        'resize_keyboard': True,
        'one_time_keyboard': False
    }
    return json.dumps(keyboard)

def remove_keyboard():
    """Убирает клавиатуру"""
    return json.dumps({'remove_keyboard': True})

def get_page(url):
    """Функция получает HTML-код страницы с таймаутом"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # Отключаем прокси для PythonAnywhere
        session = requests.Session()
        session.trust_env = False
        
        response = session.get(url, verify=False, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        logging.error(f"Ошибка при запросе к сайту {url}: {e}")
        return None

def handle_message(chat_id, text):
    """Обрабатывает сообщения от пользователя"""
    user_addresses = get_user_addresses(chat_id)
    user_state = get_user_state(chat_id)
    
    # Обрабатываем команды отмены
    if text == '❌ Отмена':
        set_user_state(chat_id, 'idle')
        send_telegram_message(chat_id, "❌ Операция отменена.", create_main_keyboard())
        return
        
    # Обрабатываем команды в зависимости от состояния
    if user_state == 'adding_address':
        if len(text) > 100:
            send_telegram_message(chat_id, "❌ Слишком длинный адрес. Максимальная длина - 100 символов.", create_main_keyboard())
            set_user_state(chat_id, 'idle')
            return
            
        new_address = text.strip()
        if new_address in user_addresses:
            send_telegram_message(chat_id, f"❌ Адрес <code>{new_address}</code> уже есть в вашем списке.", create_main_keyboard())
        else:
            user_addresses.append(new_address)
            set_user_addresses(chat_id, user_addresses)
            send_telegram_message(chat_id, f"✅ Адрес добавлен: <code>{new_address}</code>\n\nТеперь я буду отслеживать этот адрес.", create_main_keyboard())
        set_user_state(chat_id, 'idle')
        
    elif user_state == 'removing_address':
        if text.startswith('❌ '):
            address_to_remove = text[2:]
            
            if address_to_remove in user_addresses:
                user_addresses.remove(address_to_remove)
                set_user_addresses(chat_id, user_addresses)
                send_telegram_message(chat_id, f"✅ Адрес <code>{address_to_remove}</code> удален.", create_main_keyboard())
            else:
                send_telegram_message(chat_id, "❌ Адрес не найден в списке.", create_main_keyboard())
            set_user_state(chat_id, 'idle')
        
    elif text == '/start' or text == '🚀 Start':
        welcome_message = (
            "👋 <b>Добро пожаловать в бот отслеживания отключений электричества!</b>\n\n"
            "Я буду проверять график отключений на сайте yakutskenergo.ru "
            "и присылать уведомления, если найду ваши адреса.\n\n"
            "📝 <b>Как использовать:</b>\n"
            "• Добавьте адреса, которые хотите отслеживать\n"
            "• Я буду проверять график 2 раза в день (9:30 и 17:30)\n"
            "• При обнаружении адреса пришлю уведомление\n\n"
            "⚡ <b>Используйте кнопки ниже для управления:</b>"
        )
        send_telegram_message(chat_id, welcome_message, create_main_keyboard())
        
    elif text == '📋 Мои адреса':
        if user_addresses:
            addresses_text = "\n".join([f"• {addr}" for addr in user_addresses])
            message = f"📋 <b>Ваши адреса для отслеживания:</b>\n\n{addresses_text}"
        else:
            message = "❌ У вас нет добавленных адресов.\n\nИспользуйте «➕ Добавить адрес» чтобы добавить адреса."
        send_telegram_message(chat_id, message, create_main_keyboard())
        
    elif text == '➕ Добавить адрес':
        message = (
            "📝 <b>Добавление адреса</b>\n\n"
            "Пришлите адрес, который хотите отслеживать.\n\n"
            "📌 <b>Примеры:</b>\n"
            "<code>ул. Леваневского</code>\n"
            "<code>Челюскина</code>\n"
            "<code>пр. Ленина, 15</code>\n\n"
            "ℹ️ Бот будет искать точное совпадение в тексте.\n\n"
            "❌ Для отмены нажмите кнопку «Отмена»"
        )
        send_telegram_message(chat_id, message, create_cancel_keyboard())
        set_user_state(chat_id, 'adding_address')
        
    elif text == '❌ Удалить адрес':
        if user_addresses:
            send_telegram_message(chat_id, "🗑️ <b>Выберите адрес для удаления:</b>", create_remove_keyboard(user_addresses))
            set_user_state(chat_id, 'removing_address')
        else:
            send_telegram_message(chat_id, "❌ У вас нет адресов для удаления.", create_main_keyboard())
        
    elif text == '🗑️ Очистить все':
        set_user_addresses(chat_id, [])
        send_telegram_message(chat_id, "✅ Все адреса удалены.", create_main_keyboard())
        
    elif text == '🔍 Проверить сейчас':
        if user_addresses:
            message = "🔍 <b>Запускаю проверку...</b>\n\nПроверю актуальный график отключений и пришлю результаты."
            send_telegram_message(chat_id, message, remove_keyboard())
            check_news_for_user(chat_id, user_addresses, force_notify=True)
        else:
            message = "❌ У вас нет добавленных адресов.\n\nСначала добавьте адреса для отслеживания."
            send_telegram_message(chat_id, message, create_main_keyboard())
            
    elif text == '📊 Статус':
        status_message = (
            "📊 <b>Статус бота</b>\n\n"
            "✅ Бот работает\n"
            f"🕐 Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🔧 Режим: Серверный\n"
            f"⏰ Автопроверка: 9:30 и 17:30\n"
            f"📡 Статус: Онлайн 24/7\n\n"
            f"📋 Ваших адресов: {len(user_addresses)}"
        )
        send_telegram_message(chat_id, status_message, create_main_keyboard())
            
    elif text == 'ℹ️ Помощь':
        help_message = (
            "ℹ️ <b>Помощь по использованию бота</b>\n\n"
            "⚡ <b>Как это работает:</b>\n"
            "1. Добавьте адреса для отслеживания\n"
            "2. Бот проверяет график отключений 2 раза в день\n"
            "3. При обнаружении адреса вы получаете уведомление\n\n"
            "📋 <b>Команды:</b>\n"
            "• <b>📋 Мои адреса</b> - показать текущие адреса\n"
            "• <b>➕ Добавить адрес</b> - добавить новый адрес\n"
            "• <b>❌ Удалить адрес</b> - удалить конкретный адрес\n"
            "• <b>🗑️ Очистить все</b> - удалить все адреса\n"
            "• <b>🔍 Проверить сейчас</b> - немедленная проверка\n"
            "• <b>📊 Статус</b> - проверить статус бота\n\n"
            "📌 <b>Формат адресов:</b>\n"
            "Присылайте адреса в свободной форме, например:\n"
            "<code>ул. Леваневского</code>\n"
            "<code>Челюскина</code>\n"
            "<code>пр. Ленина, 15</code>\n\n"
            "⏰ <b>Автопроверка:</b> 9:30 и 17:30 ежедневно"
        )
        send_telegram_message(chat_id, help_message, create_main_keyboard())
        
    else:
        send_telegram_message(chat_id, "❌ Неизвестная команда. Используйте кнопки меню ниже ↓", create_main_keyboard())

def process_updates():
    """Обрабатывает входящие сообщения от пользователей"""
    global last_update_id
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {'timeout': 30, 'offset': last_update_id + 1}
        response = requests.get(url, params=params, timeout=35)
        
        if response.status_code == 200:
            data = response.json()
            if data['ok'] and data['result']:
                for update in data['result']:
                    if 'message' in update and 'text' in update['message']:
                        chat_id = update['message']['chat']['id']
                        text = update['message']['text']
                        logging.info(f"📨 Новое сообщение от {chat_id}: {text}")
                        handle_message(chat_id, text)
                    
                    last_update_id = max(last_update_id, update['update_id'])
                    
    except requests.exceptions.RequestException as e:
        logging.warning(f"📡 Ошибка соединения: {e}")
        time.sleep(10)
    except Exception as e:
        logging.error(f"Ошибка обработки updates: {e}")
        time.sleep(5)

def get_yesterdays_news_link(html):
    """Получаем ссылку на вчерашнюю новость"""
    soup = BeautifulSoup(html, 'html.parser')
    
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    yesterday_day = yesterday.day
    month_names = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    yesterday_month = month_names[yesterday.month]
    
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link['href']
        link_text = link.get_text(strip=True)
        
        if (str(yesterday_day) in link_text and yesterday_month in link_text):
            if href.startswith('/'):
                full_url = 'https://www.yakutskenergo.ru' + href
            else:
                full_url = href
            
            return {'url': full_url, 'title': link_text}
    
    for link in all_links:
        href = link['href']
        if href and '/press/news/' in href and href.endswith('/'):
            full_url = 'https://www.yakutskenergo.ru' + href if href.startswith('/') else href
            return {'url': full_url, 'title': link.get_text(strip=True)}
    
    return None

def parse_news_with_dates(html, user_addresses):
    """Парсим страницу и ищем адреса пользователя"""
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    page_text = soup.get_text()
    lines = page_text.split('\n')
    
    logging.info("🔍 Начинаем парсинг страницы...")
    
    current_date = None
    found_records = set()
    
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        
        date_match = re.search(r'(\d{1,2}\s+[а-я]+)\s*$', line_clean.lower())
        if date_match:
            current_date = date_match.group(1).title()
            continue
        
        if re.search(r'\d{1,2}:\d{2}', line_clean):
            if any(city in line_clean for city in ['Нюрба', 'Верхневилюйск', 'Улус', 'район']):
                continue
            
            line_lower = line_clean.lower()
            
            for address in user_addresses:
                search_address = address.lower()
                
                search_variants = [
                    search_address,
                    search_address.replace('ского', 'ская'),
                    search_address.replace('ая', 'ого'),
                    search_address + ' ',
                    ' ' + search_address,
                    search_address.replace(' ', '')
                ]
                
                for variant in search_variants:
                    if variant in line_lower and len(variant) > 3:
                        record_id = f"{current_date}_{address}_{line_clean[:50]}"
                        
                        if record_id not in found_records:
                            logging.info(f"✅ Найден адрес '{address}' в строке: {line_clean}")
                            results.append({
                                'date': current_date or 'г. Якутск',
                                'address': address,
                                'full_text': line_clean,
                                'time': extract_time_from_line(line_clean)
                            })
                            found_records.add(record_id)
                        break
                else:
                    continue
                break
    
    logging.info(f"📊 Результаты парсинга: {len(results)} записей найдено")
    return results

def extract_time_from_line(line):
    """Извлекает время из строки"""
    time_pattern = r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})'
    match = re.search(time_pattern, line)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    single_time_pattern = r'(\d{1,2}:\d{2})'
    match = re.search(single_time_pattern, line)
    if match:
        return match.group(1)
    
    return "Время не указано"

def check_news_for_user(chat_id, user_addresses, force_notify=False):
    """Проверяет новости для конкретного пользователя"""
    if not user_addresses:
        if force_notify:
            send_telegram_message(chat_id, "❌ У вас нет добавленных адресов для проверки.", create_main_keyboard())
        return None

    logging.info(f"🔍 Начинаем проверку для пользователя {chat_id}")
    
    try:
        main_html = get_page(MAIN_URL)
        if not main_html:
            if force_notify:
                send_telegram_message(chat_id, "❌ Не удалось загрузить главную страницу с графиком отключений.", create_main_keyboard())
            return None

        news_link = get_yesterdays_news_link(main_html)
        if not news_link:
            if force_notify:
                send_telegram_message(chat_id, "❌ Не найдено актуального графика отключений на сайте.", create_main_keyboard())
            return None
        
        logging.info(f"📰 Найдена новость: {news_link['title']}")
        
        news_html = get_page(news_link['url'])
        if not news_html:
            if force_notify:
                send_telegram_message(chat_id, "❌ Не удалось загрузить страницу с деталями отключений.", create_main_keyboard())
            return None
        
        parsed_data = parse_news_with_dates(news_html, user_addresses)
        logging.info(f"📊 Результат парсинга: {len(parsed_data)} записей с отключениями")
        
        cache = load_cache()
        cache_key = f"{chat_id}_{news_link['url']}"
        
        previous_result = cache.get(cache_key, {})
        current_has_outages = len(parsed_data) > 0
        previous_has_outages = previous_result.get('has_outages', False)
        
        if not force_notify and current_has_outages == previous_has_outages:
            logging.info("ℹ️ Результаты не изменились, уведомление не отправляется")
            return parsed_data
        
        if parsed_data:
            message = f"⚠️ <b>НАЙДЕНЫ ОТКЛЮЧЕНИЯ В ЯКУТСКЕ!</b> ⚠️\n\n"
            message += f"<b>Источник:</b> {news_link['url']}\n\n"
            
            grouped_by_date = {}
            seen_records = set()
            
            for record in parsed_data:
                record_key = f"{record['date']}_{record['address']}_{record['time']}_{record['full_text'][:30]}"
                if record_key not in seen_records:
                    if record['date'] not in grouped_by_date:
                        grouped_by_date[record['date']] = []
                    grouped_by_date[record['date']].append(record)
                    seen_records.add(record_key)
            
            for date, records in grouped_by_date.items():
                message += f"📅 <b>{date}</b>\n"
                
                for record in records:
                    short_text = record['full_text']
                    if len(short_text) > 100:
                        short_text = short_text[:100] + "..."
                    message += f"📍 <b>{record['address']}</b>\n"
                    message += f"🕐 <b>Время:</b> {record['time']}\n"
                    message += f"📋 {short_text}\n"
                    message += "────────────────────\n"
                
                message += "\n"
            
            send_telegram_message(chat_id, message, create_main_keyboard())
            
            cache[cache_key] = {
                'has_outages': True,
                'timestamp': datetime.datetime.now().isoformat(),
                'news_url': news_link['url']
            }
            save_cache(cache)
            
        else:
            if force_notify:
                message = (
                    "✅ <b>ОТКЛЮЧЕНИЙ В ЯКУТСКЕ НЕ НАЙДЕНО</b>\n\n"
                    f"<b>Проверенные адреса:</b>\n"
                    + "\n".join([f"• {addr}" for addr in user_addresses]) + 
                    f"\n\n<b>Ссылка:</b> {news_link['url']}\n\n"
                    "⚡ Отключений по вашим адресам в Якутске на сегодня нет!"
                )
                send_telegram_message(chat_id, message, create_main_keyboard())
            
            cache[cache_key] = {
                'has_outages': False,
                'timestamp': datetime.datetime.now().isoformat(),
                'news_url': news_link['url']
            }
            save_cache(cache)
            
        return parsed_data
            
    except Exception as e:
        logging.error(f"❌ Критическая ошибка при проверке: {e}")
        if force_notify:
            send_telegram_message(chat_id, "❌ Произошла ошибка при проверке отключений. Попробуйте позже.", create_main_keyboard())
        return None

def check_news_for_all_users():
    """Проверяет новости для всех пользователей (автоматически)"""
    user_data = load_user_data()
    last_check_time = load_last_check_time()
    current_time = datetime.datetime.now().isoformat()
    
    logging.info(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Автопроверка для всех пользователей...")
    
    for chat_id, addresses in user_data.items():
        if addresses:
            logging.info(f"Проверяем для пользователя {chat_id}...")
            check_news_for_user(chat_id, addresses, force_notify=False)
            time.sleep(1)
    
    last_check_time['last_auto_check'] = current_time
    save_last_check_time(last_check_time)

def main():
    logging.info("🤖 Бот запущен! Для остановки нажмите Ctrl+C")
    
    # Создаем файлы если их нет
    if not os.path.exists(USER_DATA_FILE):
        save_user_data({})
    if not os.path.exists(USER_STATES_FILE):
        save_user_states({})
    if not os.path.exists(CACHE_FILE):
        save_cache({})
    if not os.path.exists(LAST_CHECK_FILE):
        save_last_check_time({})
    
    last_check_time = None
    
    while True:
        try:
            process_updates()
            
            current_time = datetime.datetime.now().strftime("%H:%M")
            if current_time in CHECK_TIMES and current_time != last_check_time:
                logging.info(f"⏰ Время автоматической проверки: {current_time}")
                check_news_for_all_users()
                last_check_time = current_time
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            logging.info("\n🛑 Бот остановлен")
            break
        except Exception as e:
            logging.error(f"❌ Ошибка в главном цикле: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()