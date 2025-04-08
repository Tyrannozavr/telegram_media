import asyncio
import re
import threading
import random
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import json
import os
from requests.exceptions import ProxyError, ConnectTimeout, ConnectionError
import logging

# Настройка логирования в файл
logging.basicConfig(
    filename='bot_debug.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальная переменная для хранения времени последней успешной проверки прокси
LAST_PROXY_SUCCESS_TIME = None

# Функция проверки состояния прокси
def check_proxy_health():
    """Проверяет работоспособность текущего прокси"""
    global LAST_PROXY_SUCCESS_TIME, PROXY_ERROR_COUNT
    
    try:
        # Получаем настройки прокси
        proxies = get_proxy_settings('http')
        
        # Попробуем выполнить запрос к google.com, который редко блокируется
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get('https://www.google.com', headers=headers, proxies=proxies, timeout=10)
        
        if response.status_code == 200:
            LAST_PROXY_SUCCESS_TIME = datetime.now()
            PROXY_ERROR_COUNT = 0
            logger.info("Проверка прокси: успешно")
            return True
        else:
            logger.warning(f"Проверка прокси: неудача, статус {response.status_code}")
            PROXY_ERROR_COUNT += 1
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке прокси: {e}")
        PROXY_ERROR_COUNT += 1
        return False

# Асинхронная функция для проверки прокси перед важными запросами
async def ensure_proxy_working():
    """Проверяет работоспособность прокси и выполняет ротацию при необходимости"""
    global LAST_PROXY_SUCCESS_TIME, PROXY_ERROR_COUNT
    
    # Если прокси недавно проверялся успешно, пропускаем проверку
    if LAST_PROXY_SUCCESS_TIME and (datetime.now() - LAST_PROXY_SUCCESS_TIME).total_seconds() < 300:
        return True
        
    # Проверяем состояние прокси
    proxy_ok = check_proxy_health()
    
    # Если прокси не работает, пробуем ротировать IP
    if not proxy_ok:
        logger.warning("Прокси не работает, выполняем ротацию IP...")
        if rotate_proxy_ip(force=True):
            # Проверяем ещё раз после ротации
            await asyncio.sleep(5)  # Даем время на применение новых настроек
            proxy_ok = check_proxy_health()
            if proxy_ok:
                logger.info("Прокси снова работает после ротации IP")
            else:
                logger.error("Прокси по-прежнему не работает даже после ротации IP")
        else:
            logger.error("Не удалось выполнить ротацию IP")
            
    return proxy_ok

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


TOKEN = "7483683780:AAGGHw8NFwuZyn4BxKWJxK-AcjV1uBETAbE"

# Файлы для хранения данных
DATA_FILE = "monitoring_data.json"
SUBSCRIPTIONS_FILE = "subscriptions.json"
PAYMENTS_FILE = "payments.json"

# ID администратора (замените на свой)
ADMIN_ID = 501613334  # 

# Структура для хранения данных пользователей
user_data = {}
subscriptions = {}
payments = {}

# Настройки прокси
PROXY_SETTINGS = {
    'host': '65.109.79.176',
    'http_port': 11028,
    'socks5_port': 12028,
    'username': 'Om9OeKjQi2',
    'password': 'BMKG6RAVXE',
    'rotation_url': 'http://176.9.113.111:20005/?command=switch&api_key=gNMLTBja2JNqnZWZPcvi&m_key=2pbfHQTTXZ&port=20519',
    'rotation_minutes': 10,  # Увеличено время ротации до 10 минут
    'error_count_threshold': 3  # Порог ошибок для принудительной ротации
}

# Счетчик ошибок прокси для отслеживания необходимости ротации
PROXY_ERROR_COUNT = 0


# Конфигурация подписок
SUBSCRIPTION_PLANS = {
    "simple": {
        "name": "Простой",
        "duration": 30,  # в днях
        "price": 249,  # в рублях
        "max_urls": 1,
        "interval": 60  # в секундах
    },
    "advanced": {
        "name": "Продвинутый",
        "duration": 30,  # в днях
        "price": 549,  # в рублях
        "max_urls": 3,
        "interval": 45  # в секундах
    },
    "master": {
        "name": "Мастер",
        "duration": 30,  # в днях
        "price": 999,  # в рублях
        "max_urls": 10,
        "interval": 35  # в секундах
    },
    "pro": {
        "name": "Профи",
        "duration": 30,  # в днях
        "price": 1999,  # в рублях
        "max_urls": 50,
        "interval": 30  # в секундах
    }
}

DEFAULT_CHECK_INTERVAL = 30  # увеличено до 60 секунд для Avito
CIAN_INTERVAL = 180          # увеличено до 3 минут для ЦИАН
AUTO_RU_INTERVAL = 120       # увеличено до 2 минут для Auto.ru
RANDOM_DELAY_FACTOR = 10     # Увеличена случайная задержка до ±20 секунд
MIN_REQUEST_DELAY = 5      # Увеличена минимальная задержка между запросами
MAX_REQUEST_DELAY = 10       # Увеличена максимальная задержка между запросами

# Загрузка данных из файлов
def load_data():
    global user_data, subscriptions, payments
    # Загрузка данных мониторинга
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as file:
                user_data = json.load(file)
            logger.info(f"Данные загружены из {DATA_FILE}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            user_data = {}
    
    # Загрузка данных подписок
    # В функции load_data
if os.path.exists(SUBSCRIPTIONS_FILE):
    try:
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as file:
            subscriptions = json.load(file)
        logger.info(f"Данные подписок загружены из {SUBSCRIPTIONS_FILE}")
        
        # Проверяем и обновляем устаревшие планы подписок
        plans_updated = False
        for user_id, sub_data in subscriptions.items():
            if "plan" in sub_data and sub_data["plan"] not in SUBSCRIPTION_PLANS:
                old_plan = sub_data["plan"]
                # Преобразование старых планов в новые
                if old_plan == "trial":
                    sub_data["plan"] = "simple"
                elif old_plan == "week":
                    sub_data["plan"] = "advanced"
                elif old_plan == "month":
                    sub_data["plan"] = "master"
                else:
                    sub_data["plan"] = "simple"  # Для всех остальных случаев
                
                logger.info(f"Обновлен план пользователя {user_id}: {old_plan} -> {sub_data['plan']}")
                plans_updated = True
        
        # Сохраняем изменения, если были обновления
        if plans_updated:
            with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as file:
                json.dump(subscriptions, file, ensure_ascii=False, indent=2)
            logger.info("Планы подписок обновлены и сохранены")
            
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных подписок: {e}")
        subscriptions = {}
    
    # Загрузка данных платежей
    if os.path.exists(PAYMENTS_FILE):
        try:
            with open(PAYMENTS_FILE, 'r', encoding='utf-8') as file:
                payments = json.load(file)
            logger.info(f"Данные платежей загружены из {PAYMENTS_FILE}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных платежей: {e}")
            payments = {}

# Сохранение данных в файлы
def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(user_data, file, ensure_ascii=False, indent=2)
        logger.info(f"Данные сохранены в {DATA_FILE}")
        
        with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as file:
            json.dump(subscriptions, file, ensure_ascii=False, indent=2)
        logger.info(f"Данные подписок сохранены в {SUBSCRIPTIONS_FILE}")
        
        with open(PAYMENTS_FILE, 'w', encoding='utf-8') as file:
            json.dump(payments, file, ensure_ascii=False, indent=2)
        logger.info(f"Данные платежей сохранены в {PAYMENTS_FILE}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {e}")

# Определение типа ресурса по URL
def get_site_type(url):
    # Обработка URL мобильных приложений
    if "avito.ru" in url:
        return "avito"
    elif "cian.ru" in url:
        return "cian"
    elif "auto.ru" in url or "/amp/cars/" in url:  # Добавляем поддержку мобильных ссылок
        return "auto"
    else:
        return None

# Функция проверки и обновления состояния подписок
def check_subscriptions():
    current_time = datetime.now()
    updated = False
    
    for user_id, user_subscription in list(subscriptions.items()):
        if "expiry_date" in user_subscription:
            expiry_date = datetime.fromisoformat(user_subscription["expiry_date"])
            if current_time > expiry_date:
                logger.info(f"Подписка пользователя {user_id} истекла")
                user_subscription["active"] = False
                updated = True
    
    if updated:
        save_data()


def get_working_proxy():
    for proxy in PROXY_LIST:
        try:
            # Проверка прокси
            test_response = requests.get('https://www.avito.ru', proxies=proxy, timeout=10)
            return proxy
        except Exception:
            continue
    return None
# Флаг использования прокси (можно включать/выключать для отладки)
# Флаг использования прокси (можно включать/выключать для отладки)
USE_PROXY = False

# Глобальный словарь состояния бота для управления приоритетами
BOT_STATE = {
    "processing_command": False,  # Флаг обработки команды пользователя
    "parsing_tasks": 0  # Счетчик активных задач парсинга
}

# Семафор для ограничения параллельных задач парсинга
# Семафор для ограничения параллельных задач парсинга
parsing_semaphore = asyncio.Semaphore(1)  # Максимум 1 одновременная задача парсинга при использовании одного прокси

# Функция для получения работающего прокси
# Функция для получения настроенных прокси
def get_proxy_settings(proxy_type='http'):
    """Возвращает настройки прокси в формате, необходимом для библиотеки requests"""
    if proxy_type.lower() == 'http':
        proxy_url = f"http://{PROXY_SETTINGS['username']}:{PROXY_SETTINGS['password']}@{PROXY_SETTINGS['host']}:{PROXY_SETTINGS['http_port']}"
    else:  # socks5
        proxy_url = f"socks5://{PROXY_SETTINGS['username']}:{PROXY_SETTINGS['password']}@{PROXY_SETTINGS['host']}:{PROXY_SETTINGS['socks5_port']}"
    
    return {
        'http': proxy_url,
        'https': proxy_url
    }

def get_proxy(proxy_type='http'):
    """Обертка для получения настроек прокси для совместимости"""
    return get_proxy_settings(proxy_type)

# Функция для ротации IP
def rotate_proxy_ip(force=False):
    """Отправляет запрос на ротацию IP через API прокси"""
    global PROXY_ERROR_COUNT
    
    try:
        # Проверяем необходимость ротации на основе счетчика ошибок
        if not force and PROXY_ERROR_COUNT < PROXY_SETTINGS.get('error_count_threshold', 3):
            logger.info(f"Пропуск ротации IP, текущий счетчик ошибок: {PROXY_ERROR_COUNT}")
            return False
            
        logger.info("Выполняю ротацию IP прокси...")
        response = requests.get(PROXY_SETTINGS['rotation_url'], timeout=10)
        
        if response.status_code == 200:
            # Сбрасываем счетчик ошибок после успешной ротации
            PROXY_ERROR_COUNT = 0
            logger.info("Ротация IP успешно выполнена")
            # Даем время на применение новых настроек
            time.sleep(5)  # Увеличиваем время ожидания после ротации
            return True
        else:
            logger.error(f"Ошибка ротации IP: статус {response.status_code}, ответ: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при запросе ротации IP: {e}")
        return False

# Функция для получения данных с Авито
def fetch_avito_listings(url):
    """Получает данные с Авито по заданным параметрам"""
    try:
        # Добавляем значительную случайную задержку перед запросом
        delay = random.uniform(MIN_REQUEST_DELAY, MAX_REQUEST_DELAY)
        logger.info(f"Ожидание {delay:.2f} секунд перед запросом к Авито...")
        time.sleep(delay)
        
        # Получаем настройки прокси
        proxies = get_proxy_settings('http')  # Используем HTTP прокси
        logger.info(f"Используем прокси: {proxies['http']}")
        
        # Устанавливаем более разнообразные заголовки для имитации обычного браузера
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        
        chosen_agent = random.choice(user_agents)
        
        headers = {
            'User-Agent': chosen_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Pragma': 'no-cache',
            'Referer': 'https://www.avito.ru/',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Google Chrome";v="121", "Not;A=Brand";v="8", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        }
        
        # Используем сессию для сохранения cookies
        session = requests.Session()
        
        # Создаем "естественное" поведение - сначала посещаем главную страницу
        logger.info("Сначала посещаем главную страницу Авито для получения cookies...")
        main_page_response = session.get('https://www.avito.ru/', 
                                       headers=headers, 
                                       proxies=proxies, 
                                       timeout=30)
        
        if main_page_response.status_code != 200:
            logger.error(f"Ошибка при посещении главной страницы: статус {main_page_response.status_code}")
            
            # Увеличиваем счетчик ошибок для отслеживания проблем с прокси
            global PROXY_ERROR_COUNT
            PROXY_ERROR_COUNT += 1
            
            # Пробуем ротировать IP и повторить запрос
            if main_page_response.status_code == 403 or main_page_response.status_code == 429:
                logger.warning(f"Получен статус {main_page_response.status_code}, пробуем выполнить ротацию IP...")
                # При 403 (Forbidden) или 429 (Too Many Requests) принудительно ротируем IP
                force_rotate = main_page_response.status_code in [403, 429]
                if rotate_proxy_ip(force=force_rotate):
                    # Получаем новый прокси после ротации
                    proxies = get_proxy_settings('http')
                    logger.info(f"Повторяем запрос с новым IP через прокси")
                    
                    # Добавляем дополнительную задержку перед повторным запросом
                    time.sleep(random.uniform(5, 10))
                    
                    # Повторяем запрос с новыми настройками
                    main_page_response = session.get('https://www.avito.ru/', 
                                            headers=headers, 
                                            proxies=proxies, 
                                            timeout=30)
                    
                    if main_page_response.status_code != 200:
                        logger.error(f"После ротации IP снова получена ошибка: статус {main_page_response.status_code}")
                        # Сохраняем ответ с ошибкой для анализа
                        with open('avito_main_error.html', 'w', encoding='utf-8') as f:
                            f.write(main_page_response.text)
                        logger.info("Сохранена страница с ошибкой в файл avito_main_error.html")
                        return []
                    else:
                        logger.info("Успешное подключение после ротации IP!")
            else:
                # Всё равно продолжаем, возможно нам удастся получить нужные cookies
                with open('avito_main_error.html', 'w', encoding='utf-8') as f:
                    f.write(main_page_response.text)
                logger.info("Сохранена страница с ошибкой в файл avito_main_error.html")
        
        # Еще одна небольшая задержка перед основным запросом
        time.sleep(random.uniform(5, 10))
        
        # Добавляем cookie из основной страницы, если они есть
        cookies = session.cookies.get_dict()
        logger.info(f"Получены cookies: {cookies}")
        
        logger.info(f"Выполняю запрос к URL Авито: {url}")
        response = session.get(url, headers=headers, proxies=proxies, timeout=40)
        
        # Проверяем статус ответа
        if response.status_code != 200:
            logger.error(f"Ошибка запроса: статус {response.status_code}")
            
            # Пробуем ротировать IP если получен статус 403
            if response.status_code == 403 and rotate_proxy_ip():
                # Получаем новый прокси после ротации
                proxies = get_proxy_settings('http')
                logger.info(f"Повторяем запрос поиска с новым IP через прокси")
                
                # Небольшая задержка перед повторным запросом
                time.sleep(3)
                
                # Повторяем запрос с новыми настройками
                response = session.get(url, headers=headers, proxies=proxies, timeout=40)
                
                if response.status_code != 200:
                    logger.error(f"После ротации IP снова получена ошибка: статус {response.status_code}")
                    # Сохраняем ответ с ошибкой для анализа
                    with open('avito_error_response.html', 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.info("Сохранена страница с ошибкой в файл avito_error_response.html")
                    return []
                else:
                    logger.info("Успешное подключение к странице поиска после ротации IP!")
            else:
                # Сохраняем ответ с ошибкой для анализа
                with open('avito_error_response.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info("Сохранена страница с ошибкой в файл avito_error_response.html")
                return []
        
        logger.info(f"Успешно получен ответ от Авито (длина: {len(response.text)} символов)")
        
        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Находим карточки объявлений
        items = soup.select('[data-marker="item"]')
        logger.info(f"Найдено объявлений: {len(items)}")
        
        results = []
        
        for i, item in enumerate(items):
            try:
                logger.info(f"Обработка объявления #{i+1}")
                
                # Извлекаем данные
                item_id = item.get('id', '')
                if not item_id:
                    item_id = item.get('data-item-id', '')
                logger.info(f"ID объявления: {item_id}")
                
                # Остальной код обработки объявлений оставляем без изменений...
                
                # Ищем заголовок
                title_element = item.select_one('[data-marker="item-title"]')
                title = title_element.text.strip() if title_element else "Нет названия"
                logger.info(f"Заголовок: {title}")
                
                # Ищем цену
                price_element = item.select_one('[data-marker="item-price"]')
                price = price_element.text.strip() if price_element else "Цена не указана"
                logger.info(f"Цена: {price}")
                
                # Очищаем цену от лишних символов
                price_clean = re.sub(r'[^\d]', '', price)
                price_value = int(price_clean) if price_clean else 0
                
                # Находим URL объявления
                item_url = ""
                url_element = item.select_one('[data-marker="item-title"] a')
                
                if url_element and 'href' in url_element.attrs:
                    href = url_element['href'].strip()
                    if href.startswith('//'):
                        item_url = "https:" + href
                    elif href.startswith('/'):
                        item_url = "https://www.avito.ru" + href
                    elif href.startswith('http'):
                        item_url = href
                    else:
                        item_url = "https://www.avito.ru/" + href
                else:
                    # Пробуем альтернативные методы поиска URL
                    url_element = item.select_one('a[itemprop="url"]')
                    if url_element and 'href' in url_element.attrs:
                        href = url_element['href'].strip()
                        if href.startswith('//'):
                            item_url = "https:" + href
                        elif href.startswith('/'):
                            item_url = "https://www.avito.ru" + href
                        elif href.startswith('http'):
                            item_url = href
                        else:
                            item_url = "https://www.avito.ru/" + href
                    else:
                        all_links = item.select('a')
                        for link in all_links:
                            if 'href' in link.attrs:
                                href = link['href'].strip()
                                if '/item/' in href or '/items/' in href:
                                    if href.startswith('//'):
                                        item_url = "https:" + href
                                    elif href.startswith('/'):
                                        item_url = "https://www.avito.ru" + href
                                    elif href.startswith('http'):
                                        item_url = href
                                    else:
                                        item_url = "https://www.avito.ru/" + href
                                    break
                
                # Пытаемся получить время публикации
                time_element = item.select_one('[data-marker="item-date"]')
                pub_time = time_element.text.strip() if time_element else ""
                
                # Собираем результат
                result = {
                    'id': item_id,
                    'title': title,
                    'price': price,
                    'price_value': price_value,
                    'url': item_url,
                    'pub_time': pub_time,
                    'site': 'avito',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Проверяем, что у нас есть как минимум ID, заголовок и URL
                if item_id and title and item_url:
                    results.append(result)
                
            except Exception as e:
                logger.error(f"Ошибка при парсинге элемента Авито: {e}")
        
        logger.info(f"Успешно обработано объявлений Авито: {len(results)}")
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса к Авито: {e}")
        logger.exception(e)  # Выводим полный стек трейс
        return []

# Функция для получения данных с ЦИАН
def fetch_cian_listings(url):
    """Получает данные с ЦИАН по заданным параметрам"""
    try:
        # Добавляем значительную задержку между запросами
        delay = random.uniform(MIN_REQUEST_DELAY, MAX_REQUEST_DELAY)
        logger.info(f"Ожидание {delay:.2f} секунд перед запросом к ЦИАН...")
        time.sleep(delay)
        
        # Получаем настройки прокси
        proxies = get_proxy_settings('http')  # Используем HTTP прокси
        logger.info(f"Используем прокси для ЦИАН: {proxies['http']}")
        
        # Создаем сессию для сохранения cookies
        session = requests.Session()
        
        # Более реалистичные заголовки
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Pragma': 'no-cache',
            'sec-ch-ua': '"Google Chrome";v="121", "Not;A=Brand";v="8", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Referer': 'https://cian.ru/'
        }
        
        # Сначала посещаем главную страницу для получения cookies
        logger.info("Посещение главной страницы ЦИАН для получения cookies")
        main_page_response = session.get('https://cian.ru/', headers=headers, proxies=proxies, timeout=30)
        
        if main_page_response.status_code != 200:
            logger.error(f"Ошибка при посещении главной страницы: статус {main_page_response.status_code}")
            
            # Увеличиваем счетчик ошибок для отслеживания проблем с прокси
            global PROXY_ERROR_COUNT
            PROXY_ERROR_COUNT += 1
            
            # Пробуем ротировать IP и повторить запрос
            if main_page_response.status_code == 403 or main_page_response.status_code == 429:
                logger.warning(f"Получен статус {main_page_response.status_code}, пробуем выполнить ротацию IP...")
                # При 403 (Forbidden) или 429 (Too Many Requests) принудительно ротируем IP
                force_rotate = main_page_response.status_code in [403, 429]
                if rotate_proxy_ip(force=force_rotate):
                    # Получаем новый прокси после ротации
                    proxies = get_proxy_settings('http')
                    logger.info(f"Повторяем запрос с новым IP через прокси")
                    
                    # Добавляем дополнительную задержку перед повторным запросом
                    time.sleep(random.uniform(5, 10))
                    
                    # Повторяем запрос с новыми настройками
                    main_page_response = session.get('https://www.avito.ru/', 
                                            headers=headers, 
                                            proxies=proxies, 
                                            timeout=30)
                    
                    if main_page_response.status_code != 200:
                        logger.error(f"После ротации IP снова получена ошибка: статус {main_page_response.status_code}")
                        # Сохраняем ответ с ошибкой для анализа
                        with open('cian_main_error.html', 'w', encoding='utf-8') as f:
                            f.write(main_page_response.text)
                        logger.info("Сохранена страница с ошибкой в файл cian_main_error.html")
                        return []
                    else:
                        logger.info("Успешное подключение к ЦИАН после ротации IP!")
            else:
                # Всё равно продолжаем, возможно нам удастся получить нужные cookies
                with open('cian_main_error.html', 'w', encoding='utf-8') as f:
                    f.write(main_page_response.text)
                logger.info("Сохранена страница с ошибкой в файл cian_main_error.html")
        
        # Добавляем естественную задержку между запросами
        time.sleep(random.uniform(5, 10))

        logger.info(f"Выполняю запрос к URL ЦИАН: {url}")
        response = session.get(url, headers=headers, proxies=proxies, timeout=40)
        
        if response.status_code != 200:
            logger.error(f"Ошибка запроса к ЦИАН: статус {response.status_code}")
            
            # Пробуем ротировать IP если получен статус 403
            if response.status_code == 403 and rotate_proxy_ip():
                # Получаем новый прокси после ротации
                proxies = get_proxy_settings('http')
                logger.info(f"Повторяем запрос к ЦИАН с новым IP через прокси")
                
                # Небольшая задержка перед повторным запросом
                time.sleep(3)
                
                # Повторяем запрос с новыми настройками
                response = session.get(url, headers=headers, proxies=proxies, timeout=40)
                
                if response.status_code != 200:
                    logger.error(f"После ротации IP снова получена ошибка: статус {response.status_code}")
                    # Сохраняем ответ с ошибкой для анализа
                    with open('cian_error_response.html', 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.info("Сохранена страница с ошибкой в файл cian_error_response.html")
                    return []
                else:
                    logger.info("Успешное подключение к странице поиска ЦИАН после ротации IP!")
            else:
                # Сохраняем ответ с ошибкой для анализа
                with open('cian_error_response.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info("Сохранена страница с ошибкой в файл cian_error_response.html")
                return []
        
        logger.info(f"Успешно получен ответ от ЦИАН (длина: {len(response.text)} символов)")
        
        # Сохраняем HTML для отладки
        with open('cian_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Пробуем различные селекторы, начиная с самых новых
        selectors = [
            'article[data-name="CardComponent"]',
            'article[class*="_93444fe79c--container"]',
            'div[data-name="Offers"] article',
            'article._93444fe79c--container--PovJ',
            # Старые селекторы для обратной совместимости
            'article._93444fe79c--container--2pRrc',
            'div[data-name="Offers"] div[data-name="CardComponent"]'
        ]
        
        items = []
        used_selector = None
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                used_selector = selector
                logger.info(f"Найдены объявления ЦИАН с селектором: {selector}")
                break
        
        logger.info(f"Найдено объявлений ЦИАН: {len(items)}")
        
        if not items:
            # Попробуем найти хотя бы ссылки на объявления
            links = soup.select('a[href*="/flat/"]')
            if not links:
                links = soup.select('a[href*="/rent/"]')
            
            logger.info(f"Найдено ссылок на объявления: {len(links)}")
            
            if links:
                results = []
                for i, link in enumerate(links):
                    try:
                        href = link.get('href')
                        item_url = f"https://www.cian.ru{href}" if href.startswith('/') else href
                        
                        # Извлекаем ID из URL
                        id_match = re.search(r'/flat/(\d+)', item_url) or re.search(r'/rent/(\d+)', item_url)
                        item_id = id_match.group(1) if id_match else f"link_{i}_{int(time.time())}"
                        
                        # Находим заголовок или используем шаблон
                        title = link.get_text().strip() or "Объявление ЦИАН"
                        
                        result = {
                            'id': item_id,
                            'title': title,
                            'price': "Цена не указана",
                            'price_value': 0,
                            'url': item_url,
                            'pub_time': "Недавно",
                            'site': 'cian',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке ссылки ЦИАН: {e}")
                
                return results
            
            return []
        
        results = []
        
        for i, item in enumerate(items):
            try:
                # Ищем ID объявления
                item_id = ""
                
                # Пытаемся найти ссылку на объявление
                a_elements = item.select('a[href*="/flat/"]')
                if not a_elements:
                    a_elements = item.select('a[href*="/rent/"]')
                
                for a in a_elements:
                    href = a.get('href', '')
                    id_match = re.search(r'/flat/(\d+)', href) or re.search(r'/rent/(\d+)', href)
                    if id_match:
                        item_id = id_match.group(1)
                        break
                
                if not item_id:
                    # Если ID не найден, генерируем временный
                    item_id = f"cian_{i}_{int(time.time())}"
                
                # Ищем заголовок с учетом нового скриншота
                title_elements = (
                    item.select('div[data-name="Title"] span') or 
                    item.select('div[class*="--title--"]') or 
                    item.select('article[data-name="CardComponent"] h3') or
                    item.select('div[data-name="CardComponent"] h3') or
                    item.select('div[data-test-id="offer-card"] h3') or
                    item.select('div[data-name="OfferCard"] h3')
                )
                title = title_elements[0].text.strip() if title_elements else "Объявление ЦИАН"
                
                # Ищем цену
                price_elements = item.select('div[data-name="MainPrice"] span') or item.select('div[class*="--price--"]')
                price = price_elements[0].text.strip() if price_elements else "Цена не указана"
                
                # Очищаем цену от лишних символов
                price_clean = re.sub(r'[^\d]', '', price)
                price_value = int(price_clean) if price_clean else 0
                
                # Находим URL объявления
                item_url = ""
                for a in a_elements:
                    href = a.get('href', '')
                    if '/flat/' in href or '/rent/' in href:
                        item_url = f"https://www.cian.ru{href}" if href.startswith('/') else href
                        break
                
                # Пытаемся получить время публикации
                time_elements = item.select('div[class*="--publish--"]') or item.select('div[class*="--date--"]')
                pub_time = time_elements[0].text.strip() if time_elements else "Недавно"
                
                # Собираем результат
                result = {
                    'id': item_id,
                    'title': title,
                    'price': price,
                    'price_value': price_value,
                    'url': item_url,
                    'pub_time': pub_time,
                    'site': 'cian',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Проверяем, что у нас есть как минимум ID и URL
                if item_id and item_url:
                    results.append(result)
                
            except Exception as e:
                logger.error(f"Ошибка при парсинге элемента ЦИАН: {e}")
        
        logger.info(f"Успешно обработано объявлений ЦИАН: {len(results)}")
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса к ЦИАН: {e}")
        logger.exception(e)
        return []


# Функция для получения данных с Auto.ru
def fetch_auto_listings(url):
   """Получает данные с Auto.ru по заданным параметрам"""
   try:
       # Добавляем значительную задержку между запросами
       delay = random.uniform(MIN_REQUEST_DELAY, MAX_REQUEST_DELAY)
       logger.info(f"Ожидание {delay:.2f} секунд перед запросом к Auto.ru...")
       time.sleep(delay)
       
       # Получаем настройки прокси
       proxies = get_proxy_settings('http')  # Используем HTTP прокси
       logger.info(f"Используем прокси для Auto.ru: {proxies['http']}")
       
       # Создаем сессию для сохранения cookies
       session = requests.Session()
       
       # Более реалистичные заголовки
       headers = {
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
           'Accept-Language': 'ru',
           'Accept-Encoding': 'gzip, deflate, br',
           'sec-ch-ua': '"Google Chrome";v="121", "Not;A=Brand";v="8", "Chromium";v="121"',
           'sec-ch-ua-mobile': '?0',
           'sec-ch-ua-platform': '"Windows"',
           'Upgrade-Insecure-Requests': '1',
           'Connection': 'keep-alive',
           'Cache-Control': 'max-age=0',
           'Pragma': 'no-cache',
           'Referer': 'https://auto.ru/',
           'Sec-Fetch-Dest': 'document',
           'Sec-Fetch-Mode': 'navigate',
           'Sec-Fetch-Site': 'same-origin',
           'Sec-Fetch-User': '?1'
       }
       
       # Сначала посещаем главную страницу (как реальный пользователь)
       logger.info("Посещение главной страницы Auto.ru для получения cookies")
       main_response = session.get('https://auto.ru/', headers=headers, proxies=proxies, timeout=30)
       
       if main_response.status_code != 200:
           logger.error(f"Ошибка при посещении главной страницы Auto.ru: статус {main_response.status_code}")
           
           # Пробуем ротировать IP и повторить запрос
           if main_response.status_code == 403:
               logger.warning("Получен статус 403, пробуем выполнить ротацию IP...")
               if rotate_proxy_ip():
                   # Получаем новый прокси после ротации
                   proxies = get_proxy_settings('http')
                   logger.info(f"Повторяем запрос к Auto.ru с новым IP через прокси")
                   
                   # Повторяем запрос с новыми настройками
                   main_response = session.get('https://auto.ru/', 
                                          headers=headers, 
                                          proxies=proxies, 
                                          timeout=30)
                   
                   if main_response.status_code != 200:
                       logger.error(f"После ротации IP снова получена ошибка: статус {main_response.status_code}")
                       # Сохраняем ответ с ошибкой для анализа
                       with open('auto_main_error.html', 'w', encoding='utf-8') as f:
                           f.write(main_response.text)
                       logger.info("Сохранена страница с ошибкой в файл auto_main_error.html")
                       return []
                   else:
                       logger.info("Успешное подключение к Auto.ru после ротации IP!")
           else:
               # Всё равно продолжаем, возможно нам удастся получить нужные cookies
               with open('auto_main_error.html', 'w', encoding='utf-8') as f:
                   f.write(main_response.text)
               logger.info("Сохранена страница с ошибкой в файл auto_main_error.html")
       
       # Добавляем значительную задержку между запросами
       delay = random.uniform(5, 10)
       logger.info(f"Ожидание {delay:.2f} секунд перед запросом к Auto.ru...")
       time.sleep(delay)

       # Теперь выполняем основной запрос с теми же cookies
       logger.info(f"Выполняю запрос к URL Auto.ru: {url}")
       response = session.get(url, headers=headers, proxies=proxies, timeout=40)
       
       if response.status_code != 200:
           logger.error(f"Ошибка запроса к Auto.ru: статус {response.status_code}")
           
           # Пробуем ротировать IP если получен статус 403
           if response.status_code == 403 and rotate_proxy_ip():
               # Получаем новый прокси после ротации
               proxies = get_proxy_settings('http')
               logger.info(f"Повторяем запрос поиска к Auto.ru с новым IP через прокси")
               
               # Небольшая задержка перед повторным запросом
               time.sleep(3)
               
               # Повторяем запрос с новыми настройками
               response = session.get(url, headers=headers, proxies=proxies, timeout=40)
               
               if response.status_code != 200:
                   logger.error(f"После ротации IP снова получена ошибка: статус {response.status_code}")
                   # Сохраняем ответ с ошибкой для анализа
                   with open('auto_error_response.html', 'w', encoding='utf-8') as f:
                       f.write(response.text)
                   logger.info("Сохранена страница с ошибкой в файл auto_error_response.html")
                   return []
               else:
                   logger.info("Успешное подключение к странице поиска Auto.ru после ротации IP!")
           else:
               # Сохраняем ответ с ошибкой для анализа
               with open('auto_error_response.html', 'w', encoding='utf-8') as f:
                   f.write(response.text)
               logger.info("Сохранена страница с ошибкой в файл auto_error_response.html")
               return []
       
       # Проверяем наличие капчи в ответе
       if "captcha" in response.url or "captcha" in response.text.lower():
           logger.warning("Обнаружена капча на Auto.ru. Пробуем выполнить ротацию IP...")
           if rotate_proxy_ip():
               # Получаем новый прокси после ротации
               proxies = get_proxy_settings('http')
               logger.info(f"Повторяем запрос к Auto.ru с новым IP через прокси после обнаружения капчи")
               
               # Повторяем запрос с новыми настройками
               response = session.get(url, headers=headers, proxies=proxies, timeout=40)
               
               if "captcha" in response.url or "captcha" in response.text.lower():
                   logger.error("Капча по-прежнему обнаруживается после ротации IP. Пропускаем запрос.")
                   # Сохраняем страницу с капчей для анализа
                   with open('auto_captcha.html', 'w', encoding='utf-8') as f:
                       f.write(response.text)
                   return []
           else:
               logger.warning("Не удалось ротировать IP. Пропускаем запрос.")
               return []
           
       logger.info(f"Успешно получен ответ от Auto.ru (длина: {len(response.text)} символов)")
       
       soup = BeautifulSoup(response.text, 'html.parser')
       
       # Сохраняем для отладки
       with open('auto_debug.html', 'w', encoding='utf-8') as f:
           f.write(response.text)
       
       # Используем более точные селекторы из примера
       items = soup.find_all('div', class_='ListingItem__description')
       logger.info(f"Найдено объявлений Auto.ru: {len(items)}")
       
       # Если не нашли объявления через основной селектор, пробуем альтернативные
       if not items:
           items = soup.find_all('div', class_='ListingItem')
           logger.info(f"Найдено объявлений через альтернативный селектор: {len(items)}")
           
           # Если и это не помогло, пробуем найти по ссылкам
           if not items:
               links = soup.find_all('a', class_='Link ListingItemTitle__link')
               logger.info(f"Найдено ссылок на объявления: {len(links)}")
               if links:
                   results = []
                   for i, link in enumerate(links):
                       try:
                           item_url = link.get('href')
                           if not item_url.startswith('http'):
                               item_url = f"https://auto.ru{item_url}"
                               
                           # Извлекаем ID из URL
                           item_id = ""
                           id_match = re.search(r'/sale/(\d+)', item_url)
                           if id_match:
                               item_id = id_match.group(1)
                           else:
                               item_id = f"link_{i}_{int(time.time())}"
                               
                           # Создаем базовое объявление
                           result = {
                               'id': item_id,
                               'title': link.get_text(),
                               'price': "Цена не указана",
                               'price_value': 0,
                               'url': item_url,
                               'pub_time': "Недавно",
                               'site': 'auto',
                               'timestamp': datetime.now().isoformat()
                           }
                           
                           if item_id and item_url:
                               results.append(result)
                       except Exception as e:
                           logger.error(f"Ошибка при обработке ссылки Auto.ru: {e}")
                   
                   return results
       
       results = []
       
       for i, item in enumerate(items):
           try:
               # Ищем заголовок и ссылку
               title_element = item.find('a', 'Link ListingItemTitle__link') or item.find('a', class_=lambda c: c and 'ListingItemTitle__link' in c)
               if not title_element:
                # Дополнительные селекторы для заголовка из Auto.ru
                title_element = item.select_one('div[class*="ListingItemTitle"]') or item.select_one('h3[class*="ListingItemTitle"]')
                title = title_element.get_text().strip() if title_element else "Нет названия"
               
               # Получаем URL объявления для мобильной и десктопной версии
                item_url = ""

                # Сначала пробуем найти ссылку из заголовка
                url_selectors = [
                    'a.AmpLink.ListingAmpItemHeader_titleLink',
                    'a.AmpLink[href*="/amp/cars/used/sale/bmw/"]',
                    'a.Link[href*="/cars/used/sale/bmw/"]'
                ]

                for selector in url_selectors:
                    url_element = soup.select_one(selector)
                    if url_element and 'href' in url_element.attrs:
                        item_url = url_element['href']
                        
                        # Обработка относительных URL
                        if item_url.startswith('/'):
                            item_url = f"https://auto.ru{item_url}"
                        break

                # Если ссылка все еще не найдена, извлекаем из текущего URL
                if not item_url:
                    # Для мобильной версии Auto.ru, конвертируем AMP URL в обычный
                    if url.startswith('https://auto.ru/amp/cars/'):
                        item_url = url.replace('/amp/cars/', '/cars/')
                    else:
                        item_url = url

                # Убеждаемся, что ссылка абсолютная
                if item_url and not item_url.startswith('http'):
                    item_url = f"https://auto.ru{item_url}"
               
               # Извлекаем ID из URL
               item_id = ""
               id_match = re.search(r'/sale/(\d+)', item_url)
               if id_match:
                   item_id = id_match.group(1)
               else:
                   item_id = f"item_{i}_{int(time.time())}"
               
               # Ищем цену
               price_element = item.find('div', 'ListingItemPrice__content') or item.find('div', class_=lambda c: c and 'ListingItemPrice__content' in c)
               price = price_element.get_text().strip() if price_element else "Цена не указана"
               
               # Очищаем цену от лишних символов
               price_clean = re.sub(r'[^\d]', '', price)
               price_value = int(price_clean) if price_clean else 0
               
               # Получаем год выпуска или время публикации
               year_element = item.find('div', 'ListingItem__yearBlock') or item.find('div', class_=lambda c: c and 'ListingItem__yearBlock' in c)
               pub_time = year_element.get_text().strip() if year_element else "Недавно"
               
               # Собираем результат
               result = {
                   'id': item_id,
                   'title': title,
                   'price': price,
                   'price_value': price_value,
                   'url': item_url,
                   'pub_time': pub_time,
                   'site': 'auto',
                   'timestamp': datetime.now().isoformat()
               }
               
               # Проверяем, что у нас есть как минимум ID и URL
               if item_id and item_url:
                   results.append(result)
               
           except Exception as e:
               logger.error(f"Ошибка при парсинге элемента Auto.ru: {e}")
       
       logger.info(f"Успешно обработано объявлений Auto.ru: {len(results)}")
       return results
       
   except Exception as e:
       logger.error(f"Ошибка при выполнении запроса к Auto.ru: {e}")
       logger.exception(e)  # Выводим полный стек ошибки для отладки
       return []
# Универсальная функция получения объявлений в зависимости от сайта
def fetch_listings(url):
    site_type = get_site_type(url)
    
    if site_type == "avito":
        return fetch_avito_listings(url)
    elif site_type == "cian":
        return fetch_cian_listings(url)
    elif site_type == "auto":
        return fetch_auto_listings(url)
    else:
        logger.error(f"Неподдерживаемый тип сайта для URL: {url}")
        return []

# Функция отправки сообщения с кнопкой
async def send_listing_with_button(bot, user_id, listing):
    try:
        listing_url = listing['url']
        site_type = listing['site']
        
        # Определяем эмодзи для различных сайтов
        site_emoji = {
            "avito": "🟢",
            "cian": "🔵",
            "auto": "🔴"
        }
        
        emoji = site_emoji.get(site_type, "🔹")
        site_name = {
            "avito": "Avito",
            "cian": "ЦИАН",
            "auto": "Auto.ru"
        }.get(site_type, "")
        
        # Текст сообщения с улучшенным форматированием
        # Текст сообщения с расширенной информацией для Auto.ru
        if site_type == "auto":
            # Проверяем наличие спецификаций
            specs = listing.get('specs', {})
            
            # Формируем текст с расширенной информацией
            text = f"{emoji} <b>{listing['title']}</b>\n\n"
            
            # Основная информация: цена
            if 'full_price' in listing and 'price' in listing:
                text += f"💰 <b>{listing['full_price']} ₽</b>\n"
                text += f"💳 <b>{listing['price']}</b> (в кредит)\n\n"
            else:
                text += f"💰 <b>{listing['price']}</b>\n\n"
            
            # Добавляем спецификации, если они есть
            if specs:
                if 'Пробег' in specs:
                    text += f"🛣 Пробег: {specs['Пробег']}\n"
                if 'Двигатель' in specs:
                    text += f"⚙️ Двигатель: {specs['Двигатель']}\n"
                if 'Трансмиссия' in specs:
                    text += f"🔄 КПП: {specs['Трансмиссия']}\n"
                if 'Кузов' in specs:
                    text += f"🚘 Кузов: {specs['Кузов']}\n"
                
                text += "\n"
            
            text += f"🕒 {listing['pub_time']}\n"
            text += f"📱 {site_name}"
        else:
            # Для других платформ оставляем прежний формат
            text = (
                f"{emoji} <b>{listing['title']}</b>\n"
                f"💰 <b>{listing['price']}</b>\n"
                f"🕒 {listing['pub_time']}\n"
                f"📱 {site_name}"
            )
        
        # Кнопка для перехода на объявление
        keyboard = [[InlineKeyboardButton("Открыть объявление", url=listing_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Пытаемся получить изображение, если это Авито
        # Пытаемся получить изображение для любой платформы
        img_data = None
        try:
            # Получаем детали объявления в зависимости от типа сайта
            details = await get_listing_details(listing_url, site_type)
            
            # Если есть изображения, скачиваем первое
            if details and 'images' in details and details['images']:
                img_url = details['images'][0]
                logger.info(f"Загружаем фото с {site_name}: {img_url}")
                img_data = await download_image(img_url)
        except Exception as e:
            logger.error(f"Ошибка при получении фото для {site_name}: {e}")
        
        # Отправляем сообщение с изображением или без
        if img_data:
            logger.info("Отправляем сообщение с фото")
            await bot.send_photo(
                chat_id=user_id,
                photo=img_data,
                caption=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            # Если изображение не получено, отправляем только текст
            logger.info("Отправляем сообщение без фото")
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        
        # Резервный метод - отправляем обычный текст
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"{listing['title']}\n💰 {listing['price']}\n🕒 {listing['pub_time']}\n\n{listing_url}"
            )
            return True
        except Exception as final_error:
            logger.error(f"Критическая ошибка при отправке сообщения: {final_error}")
            return False
        
async def test_avito_images(url='https://www.avito.ru/moskva/telefony/iphone_12_128_gb_2279212408'):
    """Тестирует загрузку изображений с Авито"""
    try:
        logger.info(f"Тестирование загрузки изображений с Авито. URL: {url}")
        
        details = await get_avito_details(url)
        
        if not details:
            logger.error("Не удалось получить детали объявления")
            return False
        
        logger.info(f"Детали объявления получены. Заголовок: {details.get('title', 'Н/Д')}")
        
        images = details.get('images', [])
        logger.info(f"Изображений найдено: {len(images)}")
        
        if not images:
            logger.error("Изображения не найдены")
            return False
        
        logger.info(f"Первое изображение: {images[0]}")
        
        img_data = await download_image(images[0])
        if img_data:
            logger.info("Изображение успешно загружено!")
            return True
        else:
            logger.error("Не удалось загрузить изображение")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании загрузки изображений: {e}")
        return False

# Фоновая задача для проверки объявлений
async def check_listings(context: ContextTypes.DEFAULT_TYPE):
    # Пропускаем проверку, если обрабатывается команда
    if BOT_STATE["processing_command"]:
        logger.info("Пропуск проверки объявлений - бот обрабатывает команду пользователя")
        return
    
        # Проверяем состояние прокси перед запросом
    proxy_ok = await ensure_proxy_working()
    if not proxy_ok:
        logger.warning("Пропуск проверки объявлений - прокси не работает")
        return
        
    # Используем семафор для ограничения количества одновременных задач парсинга
    async with parsing_semaphore:
        try:
            BOT_STATE["parsing_tasks"] += 1
            
            bot = context.bot
            job = context.job
            user_id = job.data['user_id']
            url = job.data['url']
            job_name = job.data['job_name']
            
            logger.info(f"🔍 НАЧАЛО ПРОВЕРКИ: user_id={user_id}, job_name={job_name}")
            logger.info(f"URL для проверки: {url}")
            
            # Проверяем активность подписки
            if str(user_id) not in subscriptions or not subscriptions[str(user_id)].get("active", False):
                logger.warning(f"❌ Подписка для {user_id} неактивна")
                job.schedule_removal()
                return
            
            logger.info(f"Получение объявлений для URL: {url}")
            current_listings = fetch_listings(url)
            
            if not current_listings:
                logger.warning(f"❌ НЕ ПОЛУЧЕНЫ объявления для {url}")
                return
    
            logger.info(f"✅ Получено объявлений: {len(current_listings)}")
            
            # Остальной код функции
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В check_listings: {e}")
            logger.exception(e)  # Это выведет полный стек трейса
        finally:
            BOT_STATE["parsing_tasks"] -= 1
    
    logger.info(f"Проверка объявлений для пользователя {user_id}, URL: {url}")
    
    # Получаем текущие объявления
    current_listings = fetch_listings(url)
    
    if not current_listings:
        logger.warning(f"Не удалось получить объявления для {url}")
        return
    
    # Получаем сохраненные ID объявлений
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {"jobs": {}}
    
    if "jobs" not in user_data[str(user_id)]:
        user_data[str(user_id)]["jobs"] = {}
    
    if job_name not in user_data[str(user_id)]["jobs"]:
        user_data[str(user_id)]["jobs"][job_name] = {
            "url": url,
            "seen_ids": [],
            "last_check": datetime.now().isoformat(),
            "site_type": get_site_type(url)
        }
    
    job_data = user_data[str(user_id)]["jobs"][job_name]
    seen_ids = job_data["seen_ids"]
    
    # Проверяем новые объявления
    new_listings = []
    for listing in current_listings:
        if listing['id'] and listing['id'] not in seen_ids:
            new_listings.append(listing)
            seen_ids.append(listing['id'])
    
    # Ограничиваем количество сохраняемых ID (сохраняем последние 100)
    user_data[str(user_id)]["jobs"][job_name]["seen_ids"] = seen_ids[-100:]
    user_data[str(user_id)]["jobs"][job_name]["last_check"] = datetime.now().isoformat()
    
    # Сохраняем обновленные данные
    save_data()
    
    # Отправляем уведомления о новых объявлениях
    # Отправляем уведомления о новых объявлениях
    if new_listings:
        site_type = get_site_type(url)
        site_name = {
            "avito": "Avito",
            "cian": "ЦИАН",
            "auto": "Auto.ru"
        }.get(site_type, "")
        
        # Сортируем объявления по дате (если возможно)
        sorted_listings = sorted(
            new_listings,
            key=lambda x: x.get('timestamp', datetime.now().isoformat()),
            reverse=True
        )
        
        # Ограничиваем количество отправляемых объявлений до 10, чтобы не спамить
        notifications_limit = min(len(sorted_listings), 10)
        send_listings = sorted_listings[:notifications_limit]
        
        # Информируем о количестве новых объявлений, указываем ограничение если применимо
        if len(new_listings) > notifications_limit:
            notification_text = (
                f"🔔 Найдено {len(new_listings)} новых объявлений на {site_name}!\n"
                f"Отправляю {notifications_limit} самых свежих объявлений."
            )
        else:
            notification_text = f"🔔 Найдено {len(new_listings)} новых объявлений на {site_name}!"
        
        await bot.send_message(
            chat_id=user_id,
            text=notification_text
        )
        
        # Отправляем найденные объявления с увеличенными интервалами
        for listing in send_listings:
            try:
                await send_listing_with_button(bot, user_id, listing)
                # Увеличенный интервал между отправкой сообщений
                await asyncio.sleep(random.uniform(1.5, 3.0))
            except Exception as e:
                logger.error(f"Ошибка при отправке объявления: {e}")
                # Продолжаем отправку других объявлений даже при ошибке
                continue

# Функция для создания основной клавиатуры с меню
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🔍 Мои отслеживания"), KeyboardButton("💳 Подписка")],
        [KeyboardButton("📚 Инструкция"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функция для создания клавиатуры выбора подписки
def get_subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton(
            f"🔹 {SUBSCRIPTION_PLANS['simple']['name']} - {SUBSCRIPTION_PLANS['simple']['price']} ₽ ({SUBSCRIPTION_PLANS['simple']['max_urls']} ссылка)", 
            callback_data="sub_simple"
        )],
        [InlineKeyboardButton(
            f"🔷 {SUBSCRIPTION_PLANS['advanced']['name']} - {SUBSCRIPTION_PLANS['advanced']['price']} ₽ ({SUBSCRIPTION_PLANS['advanced']['max_urls']} ссылки)", 
            callback_data="sub_advanced"
        )],
        [InlineKeyboardButton(
            f"⭐ {SUBSCRIPTION_PLANS['master']['name']} - {SUBSCRIPTION_PLANS['master']['price']} ₽ ({SUBSCRIPTION_PLANS['master']['max_urls']} ссылок)", 
            callback_data="sub_master"
        )],
        [InlineKeyboardButton(
            f"🔥 {SUBSCRIPTION_PLANS['pro']['name']} - {SUBSCRIPTION_PLANS['pro']['price']} ₽ ({SUBSCRIPTION_PLANS['pro']['max_urls']} ссылок)", 
            callback_data="sub_pro"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)

# Функция для создания клавиатуры оплаты
def get_payment_keyboard(plan_id, payment_id):
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_{plan_id}_{payment_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Функция для обработки стартовой команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start"""
    user = update.effective_user
    user_id = user.id
    # Инициализируем данные пользователя, если их еще нет
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {"jobs": {}}
        save_data()
    
    # Проверяем подписку пользователя
    has_subscription = (str(user_id) in subscriptions and subscriptions[str(user_id)].get("active", False))
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🔎 Я бот для мониторинга объявлений Avito, ЦИАН и Auto.ru.\n"
        "📱 Отправь мне ссылку на поиск, и я буду уведомлять тебя о новых объявлениях.\n\n"
    )
    
    if has_subscription:
        plan_id = subscriptions[str(user_id)]["plan"]
        expiry_date = datetime.fromisoformat(subscriptions[str(user_id)]["expiry_date"])
        expiry_days = (expiry_date - datetime.now()).days
        
        welcome_text += (
            f"✅ У вас активна подписка «{SUBSCRIPTION_PLANS[plan_id]['name']}»\n"
            f"📆 Действует еще {expiry_days} дней\n"
            f"🔍 Доступно отслеживаний: {SUBSCRIPTION_PLANS[plan_id]['max_urls']}\n\n"
            "Для начала отслеживания просто пришлите ссылку!"
        )
    else:
        welcome_text += (
            "⚠️ У вас нет активной подписки.\n"
            "Для начала работы необходимо приобрести подписку.\n"
            "Нажмите «💳 Подписка» для выбора тарифа."
        )
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

# Функция для обработки команды помощи
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /help или кнопку Помощь"""
    # Создаем клавиатуру с кнопками для частых вопросов
    keyboard = [
        [InlineKeyboardButton("❓ Что делает этот бот?", url="https://telegra.ph/CHto-delaet-ehtot-bot-05-21")],
        [InlineKeyboardButton("⏰ Почему уведомления приходят позже?", url="https://telegra.ph/Pochemu-bot-prisylaet-uvedomleniya-pozzhe-vremeni-ukazannogo-v-obyavlenii-05-21")],
        [InlineKeyboardButton("📱 Как отправить ссылку на поиск?", url="https://telegra.ph/Kak-dobavit-zapros-07-01")],
        [InlineKeyboardButton("🔗 Не открывается приложение", url="https://telegra.ph/Pri-perehode-po-ssylke-ne-otkryvaetsya-prilozhenie-Avito-08-05")]
    ]
    reply_markup_inline = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "❓ Помощь по использованию бота:\n\n"
        "1. Для начала работы необходимо оформить подписку. Нажмите на кнопку «💳 Подписка».\n"
        "2. После оплаты вам станет доступно добавление ссылок для отслеживания.\n"
        "3. Чтобы добавить отслеживание, просто скопируйте и отправьте ссылку на результаты поиска с Avito, ЦИАН или Auto.ru.\n"
        "4. Бот автоматически проверяет появление новых объявлений и сразу уведомляет вас о них.\n"
        "5. При добавлении вы можете задать понятное название для каждого отслеживания.\n"
        "6. Чтобы увидеть список отслеживаемых ссылок, нажмите «🔍 Мои отслеживания».\n"
        "7. Для остановки отслеживания нажмите на соответствующую кнопку в списке отслеживаний.\n\n"
        "⏱ Частота проверки:\n"
        "• Avito: каждые 5 секунд\n"
        "• Auto.ru: каждые 15 секунд\n"
        "• ЦИАН: каждую 1 минуту\n\n"
        "🔐 Доступные команды:\n"
        "/start - перезапустить бота\n"
        "/help - эта справка\n"
        "/list - список отслеживаемых ссылок\n"
        "/check - ручная проверка всех отслеживаний\n"
        "/stop ID - остановить отслеживание\n"
        "/subscription - информация о подписке\n\n"
        "📧 По всем вопросам обращайтесь к @sergeewich9",
        reply_markup=get_main_keyboard()
    )
    
    # Отправляем второе сообщение с инлайн-кнопками для частых вопросов
    await update.message.reply_text(
        "📋 Ответы на частые вопросы:",
        reply_markup=reply_markup_inline
    )

# Функция для обработки команды инструкции
async def instruction_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку Инструкция"""
    # Создаем клавиатуру с кнопками для частых вопросов
    keyboard = [
        [InlineKeyboardButton("❓ Что делает этот бот?", url="https://telegra.ph/CHto-delaet-ehtot-bot-05-21")],
        [InlineKeyboardButton("⏰ Почему уведомления приходят позже?", url="https://telegra.ph/Pochemu-bot-prisylaet-uvedomleniya-pozzhe-vremeni-ukazannogo-v-obyavlenii-05-21")],
        [InlineKeyboardButton("📱 Как отправить ссылку на поиск?", url="https://telegra.ph/Kak-dobavit-zapros-07-01")],
        [InlineKeyboardButton("🔗 Не открывается приложение по ссылке", url="https://telegra.ph/Pri-perehode-po-ssylke-ne-otkryvaetsya-prilozhenie-Avito-08-05")]
    ]
    reply_markup_inline = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 Инструкция по настройке поиска:\n\n"
        "🔹 Для Avito:\n"
        "1. Перейдите на сайт Avito.ru\n"
        "2. Настройте поиск по нужным вам параметрам\n"
        "3. ⚠️ Обязательно выберите сортировку «По дате» ⚠️\n"
        "4. Скопируйте ссылку из адресной строки и отправьте боту\n"
        "⏱ Бот проверяет объявления Avito каждые 5 секунд\n\n"
        
        "🔹 Для ЦИАН:\n"
        "1. Перейдите на сайт CIAN.ru\n"
        "2. Настройте поиск по параметрам\n"
        "3. Рекомендуется выбрать сортировку по дате размещения\n"
        "4. Скопируйте ссылку и отправьте боту\n"
        "⏱ Бот проверяет объявления ЦИАН каждую 1 минуту\n\n"
        
        "🔹 Для Auto.ru:\n"
        "1. Перейдите на сайт Auto.ru\n"
        "2. Настройте поиск транспорта\n"
        "3. Рекомендуется сортировка по дате размещения\n"
        "4. Скопируйте ссылку и отправьте боту\n"
        "⏱ Бот проверяет объявления Auto.ru каждые 15 секунд\n\n"
        
        "📱 Как получить ссылку на телефоне:\n"
        "• iOS (iPhone): Выполните поиск в Safari → нажмите на значок «Поделиться» → выберите «Скопировать ссылку» → вставьте в сообщение боту\n"
        "• Android: Выполните поиск в браузере → нажмите и удерживайте адресную строку → «Копировать» → вставьте в сообщение боту\n\n"
        
        "⚠️ Важно: чем точнее настроен поиск, тем эффективнее работа бота! Для эффективной работы обязательно выбирайте сортировку по дате размещения.",
        reply_markup=get_main_keyboard()
    )
    
    # Отправляем второе сообщение с инлайн-кнопками для частых вопросов
    await update.message.reply_text(
        "📋 Частые вопросы и проблемы:\n"
        "Нажмите на интересующий вас вопрос для получения подробной информации",
        reply_markup=reply_markup_inline
    )

# Функция для обработки отображения и изменения подписки
async def subscription_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /subscription или кнопку Подписка"""
    user_id = str(update.effective_user.id)
    
    # Проверяем активную подписку
    if user_id in subscriptions and subscriptions[user_id].get("active", False):
        plan_id = subscriptions[user_id]["plan"]
        # Проверяем, существует ли выбранный тариф (для совместимости со старыми данными)
        if plan_id not in SUBSCRIPTION_PLANS:
            # Если старый тариф не существует, устанавливаем "simple" как дефолт
            plan_id = "simple"
            subscriptions[user_id]["plan"] = plan_id
            save_data()
            
        expiry_date = datetime.fromisoformat(subscriptions[user_id]["expiry_date"])
        start_date = datetime.fromisoformat(subscriptions[user_id]["start_date"])
        
        days_left = (expiry_date - datetime.now()).days
        
        # Получаем количество активных отслеживаний
        active_tracking = 0
        if user_id in user_data and "jobs" in user_data[user_id]:
            active_tracking = len(user_data[user_id]["jobs"])
        
        # Информация о частоте проверки для разных платформ
        check_intervals = {
            "avito": "5 секунд",
            "cian": "1 минута",
            "auto": "15 секунд"
        }
        
        # Текст с информацией о подписке
        sub_text = (
            f"💳 Информация о вашей подписке:\n\n"
            f"📋 Тариф: «{SUBSCRIPTION_PLANS[plan_id]['name']}»\n"
            f"📅 Дата начала: {start_date.strftime('%d.%m.%Y')}\n"
            f"📅 Действует до: {expiry_date.strftime('%d.%m.%Y')}\n"
            f"⏳ Осталось дней: {days_left}\n"
            f"🔍 Активных отслеживаний: {active_tracking}/{SUBSCRIPTION_PLANS[plan_id]['max_urls']}\n\n"
            f"⏱ Частота проверки для разных платформ:\n"
            f"• Avito: каждые {check_intervals['avito']}\n"
            f"• Auto.ru: каждые {check_intervals['auto']}\n"
            f"• ЦИАН: каждую {check_intervals['cian']}\n\n"
        )

# Обработчик выбора подписки
async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает выбор подписки через InlineKeyboard"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    callback_data = query.data
    
    if callback_data.startswith("sub_"):
        # Выбор подписки
        plan_id = callback_data[4:]  # Получаем план из callback_data
        
        if plan_id in SUBSCRIPTION_PLANS:
            # Создаем запись о платеже
            payment_id = f"payment_{int(time.time())}_{user_id}"
            payment_info = {
                "id": payment_id,
                "user_id": user_id,
                "plan_id": plan_id,
                "amount": SUBSCRIPTION_PLANS[plan_id]["price"],
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
            
            # Сохраняем информацию о платеже
            if "payments" not in payments:
                payments["payments"] = {}
            payments["payments"][payment_id] = payment_info
            save_data()
            
            # Отправляем сообщение с запросом оплаты
            await query.edit_message_text(
                f"💳 Оформление подписки «{SUBSCRIPTION_PLANS[plan_id]['name']}»\n\n"
                f"Стоимость: {SUBSCRIPTION_PLANS[plan_id]['price']} ₽\n"
                f"Длительность: {SUBSCRIPTION_PLANS[plan_id]['duration']} дней\n"
                f"Кол-во отслеживаний: {SUBSCRIPTION_PLANS[plan_id]['max_urls']}\n"
                f"Интервал проверки: {SUBSCRIPTION_PLANS[plan_id]['interval']} сек\n\n"
                f"Для оплаты нажмите кнопку ниже:",
                reply_markup=get_payment_keyboard(plan_id, payment_id)
            )
    
    elif callback_data.startswith("pay_"):
        # Имитация процесса оплаты
        _, plan_id, payment_id = callback_data.split("_", 2)
        
        # В реальном боте здесь была бы интеграция с платежной системой
        # Для прототипа просто "одобряем" платеж
        
        await query.edit_message_text("⏳ Обрабатываем ваш платеж...")
        
        # Имитируем задержку обработки
        await asyncio.sleep(2)
        
        # Активируем подписку
        if plan_id in SUBSCRIPTION_PLANS:
            start_date = datetime.now()
            expiry_date = start_date + timedelta(days=SUBSCRIPTION_PLANS[plan_id]["duration"])
            
            # Обновляем информацию о подписке
            subscriptions[user_id] = {
                "active": True,
                "plan": plan_id,
                "start_date": start_date.isoformat(),
                "expiry_date": expiry_date.isoformat()
            }
            
            # Обновляем статус платежа
            if "payments" in payments and payment_id in payments["payments"]:
                payments["payments"][payment_id]["status"] = "completed"
                payments["payments"][payment_id]["completed_at"] = datetime.now().isoformat()
            
            save_data()
            
            # Отправляем сообщение об успешной оплате
            await query.edit_message_text(
                f"✅ Подписка «{SUBSCRIPTION_PLANS[plan_id]['name']}» успешно оформлена!\n\n"
                f"📅 Действует до: {expiry_date.strftime('%d.%m.%Y')}\n"
                f"🔍 Доступно отслеживаний: {SUBSCRIPTION_PLANS[plan_id]['max_urls']}\n\n"
                "Теперь вы можете добавлять ссылки для отслеживания!"
            )
    
    elif callback_data == "cancel_payment":
        await query.edit_message_text(
            "❌ Оплата отменена.\n\n"
            "Выберите другой тариф или попробуйте позже:",
            reply_markup=get_subscription_keyboard()
        )
    
    elif callback_data == "extend_subscription":
        # Продление подписки - показываем те же тарифы
        await query.edit_message_text(
            "💳 Продление подписки\n\n"
            "Выберите тариф для продления:",
            reply_markup=get_subscription_keyboard()
        )
    
    elif callback_data == "upgrade_subscription":
        # Улучшение тарифа - показываем доступные тарифы выше текущего
        current_plan = subscriptions[user_id]["plan"]
        plans_order = ["trial", "week", "month"]
        
        current_index = plans_order.index(current_plan)
        upgrade_keyboard = []
        
        for i in range(current_index + 1, len(plans_order)):
            plan_id = plans_order[i]
            upgrade_keyboard.append([
                InlineKeyboardButton(
                    f"⬆️ {SUBSCRIPTION_PLANS[plan_id]['name']} - {SUBSCRIPTION_PLANS[plan_id]['price']} ₽",
                    callback_data=f"sub_{plan_id}"
                )
            ])
        
        if not upgrade_keyboard:
            await query.edit_message_text(
                "✅ У вас уже максимальный тариф!\n\n"
                "Если хотите продлить текущую подписку, нажмите кнопку «Продлить».",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Продлить подписку", callback_data="extend_subscription")
                ]])
            )
        else:
            await query.edit_message_text(
                "⬆️ Улучшение тарифа\n\n"
                "Выберите новый тариф:",
                reply_markup=InlineKeyboardMarkup(upgrade_keyboard)
            )

# Функция для отображения списка отслеживаемых ссылок
async def list_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку Мои отслеживания или команду /list"""
    user_id = str(update.effective_user.id)
    
    # Проверяем подписку
    if user_id not in subscriptions or not subscriptions[user_id].get("active", False):
        await update.message.reply_text(
            "⚠️ У вас нет активной подписки.\n"
            "Для отслеживания объявлений необходимо оформить подписку.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Проверяем наличие отслеживаний
    if user_id not in user_data or "jobs" not in user_data[user_id] or not user_data[user_id]["jobs"]:
        await update.message.reply_text(
            "🔍 У вас пока нет отслеживаемых ссылок.\n\n"
            "Чтобы добавить отслеживание, просто отправьте ссылку на поиск с Avito, ЦИАН или Auto.ru.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Формируем список отслеживаний
    jobs = user_data[user_id]["jobs"]
    message = "📋 Ваши активные отслеживания:\n\n"
    
    site_emoji = {
        "avito": "🟢",
        "cian": "🔵",
        "auto": "🔴"
    }
    
    for job_id, job_info in jobs.items():
        url = job_info.get("url", "Ссылка недоступна")
        site_type = job_info.get("site_type", "")
        emoji = site_emoji.get(site_type, "🔹")
        
        # Форматируем время последней проверки
        last_check = "Никогда"
        if "last_check" in job_info:
            try:
                last_check_dt = datetime.fromisoformat(job_info["last_check"])
                last_check = last_check_dt.strftime("%d.%m.%Y %H:%M:%S")
            except:
                pass
        
        job_name = job_info.get("name", f"Отслеживание {job_id}")
        expiry_date = "Неизвестно"
        if "expiry_date" in job_info:
            try:
                exp_date = datetime.fromisoformat(job_info["expiry_date"])
                expiry_date = exp_date.strftime("%d.%m.%Y")
            except:
                pass

        message += f"{emoji} <b>{job_name}</b>\n"
        message += f"🔗 <b>URL:</b> {url[:50]}...\n"
        message += f"🕒 <b>Последняя проверка:</b> {last_check}\n"
        message += f"📆 <b>Активно до:</b> {expiry_date}\n"
        message += f"🆔 ID: {job_id}\n\n"
    
    # Информация о лимитах
    plan = subscriptions[user_id]["plan"]
    current_count = len(jobs)
    max_count = SUBSCRIPTION_PLANS[plan]["max_urls"]
    
    message += f"📊 Использовано {current_count} из {max_count} доступных отслеживаний"
    
    # Создаем инлайн-клавиатуру для удаления отслеживаний
    keyboard = []
    for job_id in jobs:
        keyboard.append([InlineKeyboardButton(f"❌ Остановить {job_id}", callback_data=f"stop_{job_id}")])
    
    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(message, parse_mode='HTML')


# Функция для загрузки изображений по URL
async def download_image(url):
    """Скачивает изображение по URL с повторными попытками"""
    max_retries = 3
    retry_delay = 1
    
    # Проверка и исправление URL
    if not url:
        logger.error("Пустой URL изображения")
        return None
    
    # Исправляем URL если он в формате data-marker
    if url.startswith('slider-image/image-'):
        url = url.replace('slider-image/image-', '')
    
    # Исправляем относительные URL
    if url.startswith('//'):
        url = f'https:{url}'
    
    logger.info(f"Скачиваем изображение: {url}")
    
    # Добавляем случайную задержку перед скачиванием
    await asyncio.sleep(random.uniform(1.0, 2.0))
    
    for attempt in range(max_retries):
        try:
            # Более реалистичные заголовки для скачивания изображений
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.avito.ru/',
                'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            # Используем обычные requests вместо асинхронных для совместимости
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"Ошибка при скачивании изображения: статус {response.status_code}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Увеличиваем задержку для следующей попытки
                continue
            
            # Проверяем, что контент - изображение
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('image/'):
                logger.info(f"Успешно скачано изображение: {url[:50]}...")
                return response.content
            else:
                logger.warning(f"Неверный тип контента: {content_type}")
        
        except Exception as e:
            logger.error(f"Ошибка при скачивании изображения (попытка {attempt+1}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
    
    logger.error(f"Не удалось скачать изображение после {max_retries} попыток: {url[:50]}...")
    return None

# Функция для извлечения URL изображений из страницы объявления
async def extract_images_from_listing(url, site_type):
    """Извлекает URL изображений из страницы объявления"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        logger.info(f"Получение данных со страницы объявления через прокси: {url}")
        proxies = get_proxy()
        
        # Добавляем случайную задержку перед запросом
        await asyncio.sleep(random.uniform(3, 7))
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        
        # Обработка статус-кодов ошибок
        if response.status_code != 200:
            global PROXY_ERROR_COUNT
            PROXY_ERROR_COUNT += 1
            
            if response.status_code in [403, 429]:
                logger.warning(f"Ошибка {response.status_code} при получении данных объявления, пробуем ротацию IP")
                rotate_proxy_ip(force=True)
                # Пробуем повторить запрос после короткой задержки
                await asyncio.sleep(5)
                proxies = get_proxy()
                response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при загрузке страницы объявления: статус {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        image_urls = []
        
        if site_type == "avito":
            # Извлечение изображений с Avito
            image_divs = soup.select('div.gallery-img-frame img') or soup.select('div[data-marker="item-photo"] img')
            for img in image_divs:
                if 'src' in img.attrs:
                    img_url = img['src']
                    # Проверяем, что это не заглушка и не иконка
                    if img_url and not img_url.endswith('.svg') and not img_url.endswith('.gif'):
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        image_urls.append(img_url)
        
        elif site_type == "cian":
            # Извлечение изображений с ЦИАН
            image_tags = soup.select('img[data-name="ThumbGalleryImage"]') or soup.select('img.fotorama__img')
            for img in image_tags:
                if 'src' in img.attrs:
                    img_url = img['src']
                    if img_url and not img_url.endswith('.svg'):
                        image_urls.append(img_url)
        
        elif site_type == "auto":
            # Извлечение изображений с Auto.ru
            image_tags = soup.select('img.ImageGalleryDesktop__image') or soup.select('div.Gallery__image img')
            for img in image_tags:
                if 'src' in img.attrs:
                    img_url = img['src']
                    if img_url and not img_url.endswith('.svg'):
                        image_urls.append(img_url)
        
        # Ограничиваем количество изображений для отправки
        return image_urls[:5]  # Отправляем максимум 5 изображений
    
    except Exception as e:
        logger.error(f"Ошибка при извлечении изображений: {e}")
        return []

# Функция для остановки отслеживания
async def stop_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /stop ID"""
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите ID отслеживания для остановки.\n"
            "Например: /stop job_12345\n\n"
            "Чтобы увидеть все активные отслеживания, используйте команду /list",
            reply_markup=get_main_keyboard()
        )
        return
    
    job_id = context.args[0]
    
    # Проверяем наличие отслеживания
    if (user_id not in user_data or 
        "jobs" not in user_data[user_id] or 
        job_id not in user_data[user_id]["jobs"]):
        await update.message.reply_text(
            f"❌ Отслеживание с ID {job_id} не найдено.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Останавливаем задачу в планировщике
    current_jobs = context.job_queue.get_jobs_by_name(job_id)
    for job in current_jobs:
        job.schedule_removal()
    
    # Удаляем отслеживание из данных пользователя
    del user_data[user_id]["jobs"][job_id]
    save_data()
    
    await update.message.reply_text(
        f"✅ Отслеживание с ID {job_id} успешно остановлено.",
        reply_markup=get_main_keyboard()
    )

# Функция для обработки остановки отслеживания через инлайн-кнопку
async def stop_tracking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие инлайн-кнопки остановки отслеживания"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    callback_data = query.data
    
    if callback_data.startswith("stop_"):
        job_id = callback_data[5:]  # Получаем ID задачи
        
        # Проверяем наличие отслеживания
        if (user_id in user_data and 
            "jobs" in user_data[user_id] and 
            job_id in user_data[user_id]["jobs"]):
            
            try:
                # Более надежный способ остановки задачи
                job_stopped = False
                
                # Проверяем job_queue непосредственно через context
                if hasattr(context, 'job_queue') and context.job_queue:
                    current_jobs = context.job_queue.get_jobs_by_name(job_id)
                    for job in current_jobs:
                        job.schedule_removal()
                        job_stopped = True
                
                # Если job_queue недоступен или нет задач, пробуем через application
                if not job_stopped and hasattr(context, 'application') and context.application:
                    if hasattr(context.application, 'job_queue') and context.application.job_queue:
                        current_jobs = context.application.job_queue.get_jobs_by_name(job_id)
                        for job in current_jobs:
                            job.schedule_removal()
                            job_stopped = True
                
                # Удаляем отслеживание из данных пользователя
                job_name = user_data[user_id]["jobs"][job_id].get("name", f"с ID {job_id}")
                del user_data[user_id]["jobs"][job_id]
                save_data()
                
                # Отправляем сообщение об успешной остановке с названием отслеживания
                await query.edit_message_text(
                    f"✅ Отслеживание «{job_name}» успешно остановлено."
                )
                
            except Exception as e:
                logger.error(f"Ошибка при остановке отслеживания: {e}")
                
                # Все равно удаляем из данных пользователя
                try:
                    del user_data[user_id]["jobs"][job_id]
                    save_data()
                    await query.edit_message_text(
                        f"✅ Отслеживание с ID {job_id} удалено, но могут возникнуть проблемы с планировщиком."
                    )
                except:
                    await query.edit_message_text(
                        f"❌ Возникла ошибка при удалении отслеживания. Пожалуйста, попробуйте позже."
                    )
        else:
            await query.edit_message_text(
                f"❌ Отслеживание с ID {job_id} не найдено или уже остановлено."
            )

# Функция с повторными попытками при запросах
def make_request_with_retry(url, headers, max_retries=3, proxy_type='http'):
    """Выполняет запрос с повторными попытками при ошибках"""
    for attempt in range(max_retries):
        try:
            proxies = get_proxy(proxy_type)
            
            logger.info(f"Попытка {attempt+1} запроса к {url}{' через прокси' if proxies else ''}")
            response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            
            # Проверяем капчу
            if "captcha" in response.url.lower() or "captcha" in response.text.lower():
                logger.warning(f"Обнаружена капча при запросе. Попытка {attempt+1}")
                if attempt < max_retries - 1:
                    time.sleep(5 + attempt * 5)  # Увеличиваем задержку с каждой попыткой
                    continue
            
            # Проверяем статус
            if response.status_code != 200:
                logger.warning(f"Статус ответа {response.status_code}. Попытка {attempt+1}")
                if attempt < max_retries - 1:
                    time.sleep(3 + attempt * 3)
                    continue
                    
            return response
            
        except Exception as e:
            logger.error(f"Ошибка запроса (попытка {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 + attempt * 3)
            else:
                logger.error(f"Все попытки запроса к {url} неудачны")
                raise
    
    return None

# Универсальная функция получения подробной информации об объявлении
async def get_listing_details(url, site_type):
    """Получает подробную информацию об объявлении в зависимости от типа сайта"""
    # Повторяем попытки с разными прокси в случае ошибок
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if site_type == "avito":
                return await get_avito_details(url)
            elif site_type == "cian":
                return await get_cian_details(url)
            elif site_type == "auto":
                return await get_auto_details(url)
            else:
                logger.error(f"Неподдерживаемый тип сайта для URL: {url}")
                return {}
        except (ProxyError, ConnectTimeout, ConnectionError) as e:
            logger.error(f"Ошибка прокси при получении деталей (попытка {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # Пауза перед следующей попыткой
            else:
                logger.error(f"Не удалось получить детали после {max_retries} попыток")
                return {}
        except Exception as e:
            logger.error(f"Общая ошибка при получении деталей: {e}")
            return {}


async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ручная проверка отслеживаемых объявлений"""
    user_id = str(update.effective_user.id)
    
    if user_id not in subscriptions or not subscriptions[user_id].get("active", False):
        await update.message.reply_text(
            "⚠️ У вас нет активной подписки для отслеживания объявлений.",
            reply_markup=get_main_keyboard()
        )
        return
    
    if user_id not in user_data or "jobs" not in user_data[user_id] or not user_data[user_id]["jobs"]:
        await update.message.reply_text(
            "🔍 У вас нет активных отслеживаний. Отправьте ссылку для добавления отслеживания.",
            reply_markup=get_main_keyboard()
        )
        return
    
    status_msg = await update.message.reply_text("⏳ Проверяю объявления...")
    
    # Счетчики для результатов
    checked_count = 0
    new_items_found = 0
    
    # Функция для проверки одного отслеживания
    async def check_single_job(job_id, job_info):
        job_url = job_info.get("url")
        job_site_type = job_info.get("site_type", "")
        
        if not job_url:
            return job_id, None, job_site_type
        
        # Получаем текущие объявления
        job_listings = fetch_listings(job_url)
        
        if not job_listings:
            logger.warning(f"Не удалось получить объявления для {job_url}")
            return job_id, None, job_site_type
        
        # Получаем ID уже просмотренных объявлений
        job_seen_ids = job_info.get("seen_ids", [])
        
        # Находим новые объявления
        job_new_listings = []
        for job_listing in job_listings:
            if job_listing['id'] and job_listing['id'] not in job_seen_ids:
                job_new_listings.append(job_listing)
                job_seen_ids.append(job_listing['id'])
        
        return job_id, job_listings, job_site_type, job_seen_ids, job_new_listings

    # Запускаем проверки параллельно для всех отслеживаний
    job_tasks = []
    for job_id, job_info in user_data[user_id]["jobs"].items():
        job_tasks.append(check_single_job(job_id, job_info))

    # Выполняем все задачи параллельно
    job_results = await asyncio.gather(*job_tasks)

    # Обрабатываем результаты
    for result in job_results:
        job_id = result[0]
        job_listings = result[1]
        
        if job_listings:
            checked_count += 1
            job_site_type = result[2]
            job_seen_ids = result[3]
            job_new_listings = result[4]
            
            # Обновляем данные
            user_data[user_id]["jobs"][job_id]["seen_ids"] = job_seen_ids[-100:]  # Сохраняем последние 100
            user_data[user_id]["jobs"][job_id]["last_check"] = datetime.now().isoformat()
            
            # Отправляем уведомления о новых объявлениях
            if job_new_listings:
                new_items_found += len(job_new_listings)
                site_names = {
                    "avito": "Avito",
                    "cian": "ЦИАН",
                    "auto": "Auto.ru"
                }
                site_name = site_names.get(job_site_type, "")
                
                await update.message.reply_text(
                    f"🔔 Найдено {len(job_new_listings)} новых объявлений на {site_name}!"
                )
                
                # Отправляем информацию о каждом новом объявлении
                for listing in job_new_listings:
                    await send_listing_with_button(context.bot, update.effective_user.id, listing)
                    await asyncio.sleep(0.3)  # Уменьшенная задержка между сообщениями
    
    # Сохраняем обновленные данные
    save_data()
    
    # Отправляем итоговое сообщение
    if checked_count == 0:
        await status_msg.edit_text(
            "❌ Не удалось проверить ни одно отслеживание. Попробуйте позже."
        )
    elif new_items_found == 0:
        await status_msg.edit_text(
            f"✅ Проверка завершена! Проверено {checked_count} отслеживаний параллельно.\n"
            "Новых объявлений не найдено."
        )
    else:
        await status_msg.edit_text(
            f"✅ Проверка завершена! Проверено {checked_count} отслеживаний параллельно.\n"
            f"Найдено {new_items_found} новых объявлений."
        )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE, quick_response=None) -> None:
    """Обрабатывает отправленные ссылки"""
    user_id = str(update.effective_user.id)
    url = update.message.text.strip()
    
    # Усиленное логирование
    logger.info(f"handle_url запущен для пользователя {user_id}")
    logger.info(f"Текст сообщения: {url}")
    logger.info(f"Состояние: waiting_for_name={context.user_data.get('waiting_for_name', False)}, pending_url={context.user_data.get('pending_url', 'нет')}")
    
    try:
        # Проверяем, ожидаем ли имя для сохраненной ссылки
        if context.user_data.get("waiting_for_name", False):
            logger.info("Получено имя для отслеживания, продолжаем обработку...")
            # Получаем имя из сообщения и URL из сохраненных данных
            name = url
            url = context.user_data.get("pending_url", "")
            
            # Сбрасываем флаги ожидания
            context.user_data["waiting_for_name"] = False
            context.user_data["pending_url"] = ""
            
            # Проверяем наличие сохраненной ссылки
            if not url:
                logger.error("Сохраненная ссылка отсутствует!")
                await update.message.reply_text(
                    "⚠️ Ошибка: не найдена сохраненная ссылка. Пожалуйста, отправьте ссылку заново.",
                    reply_markup=get_main_keyboard()
                )
                return
                
            logger.info(f"Продолжаем с URL: {url} и именем: {name}")
            
            # Определяем тип сайта
            site_type = get_site_type(url)
            logger.info(f"Определен тип сайта: {site_type}")
            
            # Проверяем активность подписки
            if user_id not in subscriptions or not subscriptions[user_id].get("active", False):
                logger.info(f"У пользователя {user_id} нет активной подписки")
                await update.message.reply_text(
                    "⚠️ У вас нет активной подписки.\n"
                    "Для отслеживания объявлений необходимо оформить подписку.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💳 Оформить подписку", callback_data="show_subscription_plans")
                    ]])
                )
                return
            
            # Проверяем лимит отслеживаемых ссылок
            plan = subscriptions[user_id]["plan"]
            max_urls = SUBSCRIPTION_PLANS[plan]["max_urls"]
            
            current_urls = 0
            if user_id in user_data and "jobs" in user_data[user_id]:
                current_urls = len(user_data[user_id]["jobs"])
            
            logger.info(f"Текущее количество отслеживаний: {current_urls}, максимум: {max_urls}")
            
            if current_urls >= max_urls:
                await update.message.reply_text(
                    f"⚠️ Достигнут лимит отслеживаемых ссылок ({max_urls}).\n"
                    "Для добавления новой ссылки сначала остановите одно из текущих отслеживаний или улучшите тариф.",
                    reply_markup=get_main_keyboard()
                )
                return
            
            # Отправляем сообщение о начале обработки
            processing_msg = await update.message.reply_text("⏳ Проверяю ссылку и добавляю отслеживание...")
            
            # Пробуем получить объявления для проверки
            logger.info(f"Пробуем получить объявления по URL: {url}")
            try:
                # Используем executor для блокирующей операции
                test_listings = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: fetch_listings(url)
                )
                
                logger.info(f"Получено объявлений: {len(test_listings) if test_listings else 0}")
                
                if not test_listings:
                    await processing_msg.edit_text(
                        "⚠️ Не удалось получить объявления по этой ссылке.\n"
                        f"Возможно, на {site_type.upper()} временные проблемы или изменилась структура сайта.\n"
                        "Попробуйте позже или другую ссылку.",
                        reply_markup=get_main_keyboard()
                    )
                    return
                
                # Создаем ID для отслеживания
                job_id = f"job_{int(time.time())}"
                logger.info(f"Создан ID задания: {job_id}")
                
                # Получаем интервал проверки из плана подписки
                base_interval = SUBSCRIPTION_PLANS[plan]["interval"]
                
                # Инициализируем структуры данных при необходимости
                if user_id not in user_data:
                    user_data[user_id] = {}
                if "jobs" not in user_data[user_id]:
                    user_data[user_id]["jobs"] = {}
                
                # Сохраняем данные отслеживания
                user_data[user_id]["jobs"][job_id] = {
                    "url": url,
                    "name": name,
                    "seen_ids": [listing["id"] for listing in test_listings if "id" in listing],
                    "created_at": datetime.now().isoformat(),
                    "last_check": datetime.now().isoformat(),
                    "site_type": site_type,
                    "expiry_date": (datetime.now() + timedelta(days=30)).isoformat()
                }
                
                # Сохраняем данные
                logger.info("Вызываем save_data_async")
                await save_data_async()
                logger.info("save_data_async выполнен")
                
                # Определяем интервал проверки в зависимости от типа сайта
                if site_type == "auto":
                    actual_interval = min(base_interval, 45)
                elif site_type == "cian":
                    actual_interval = min(base_interval, 60)
                else:  # avito
                    actual_interval = min(base_interval, 30)
                
                # Добавляем случайность к интервалу
                check_interval = actual_interval + random.randint(-3, 3)
                check_interval = max(check_interval, 10)  # Минимум 10 секунд
                
                logger.info(f"Интервал проверки: {check_interval} сек для сайта {site_type}")
                
                # Определяем название сайта
                site_names = {"avito": "Avito", "cian": "ЦИАН", "auto": "Auto.ru"}
                site_name = site_names.get(site_type, "")
                
                # Добавляем задачу в планировщик
                scheduled = False
                try:
                    logger.info("Пробуем добавить задачу в планировщик")
                    if hasattr(context, 'job_queue') and context.job_queue:
                        # Удаляем старые задачи с тем же ID
                        current_jobs = context.job_queue.get_jobs_by_name(job_id)
                        for job in current_jobs:
                            job.schedule_removal()
                            logger.info(f"Удалена старая задача {job_id}")
                        
                        # Добавляем новую задачу
                        context.job_queue.run_repeating(
                            check_listings,
                            interval=check_interval,
                            first=10,  # Первая проверка через 10 секунд
                            name=job_id,
                            data={
                                'user_id': int(user_id),
                                'url': url,
                                'job_name': job_id
                            }
                        )
                        scheduled = True
                        logger.info(f"Задача {job_id} успешно добавлена в планировщик")
                    else:
                        logger.error("job_queue недоступен!")
                        user_data[user_id]["manual_check"] = True
                except Exception as job_error:
                    logger.error(f"Ошибка при добавлении задачи: {job_error}")
                    logger.exception(job_error)
                    user_data[user_id]["manual_check"] = True
                
                # Формируем результат
                result_message = f"✅ Отслеживание {site_name} успешно добавлено!\n\n"
                result_message += f"📝 Название: {name}\n"
                result_message += f"🔗 URL: {url[:50]}...\n"
                result_message += f"🆔 ID отслеживания: {job_id}\n"
                result_message += f"📊 Найдено объявлений: {len(test_listings)}\n\n"
                result_message += f"Вы получите уведомление, как только появятся новые объявления."
                
                # Отправляем результат
                logger.info("Отправляем сообщение об успешном добавлении")
                await processing_msg.edit_text(
                    result_message,
                    reply_markup=get_main_keyboard()
                )
                
                # Отправляем дополнительную информацию
                if scheduled:
                    await update.message.reply_text(
                        f"⏱ Интервал проверки: {check_interval} секунд\n"
                        f"🔄 Автоматическая проверка настроена успешно",
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ Автоматические проверки недоступны. Используйте команду /check для ручной проверки.",
                        reply_markup=get_main_keyboard()
                    )
                
            except Exception as process_error:
                logger.error(f"Ошибка при обработке URL после получения имени: {process_error}")
                logger.exception(process_error)
                await processing_msg.edit_text(
                    f"❌ Произошла ошибка при добавлении отслеживания: {str(process_error)[:100]}...\n"
                    "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                    reply_markup=get_main_keyboard()
                )
        
        else:
            # Это новая ссылка
            logger.info("Получена новая ссылка, проверяем тип сайта")
            
            # Проверяем тип сайта
            site_type = get_site_type(url)
            logger.info(f"Тип сайта: {site_type}")
            
            if not site_type:
                await update.message.reply_text(
                    "⚠️ Пожалуйста, отправьте корректную ссылку на поиск с одного из поддерживаемых сайтов:\n"
                    "- Avito.ru\n"
                    "- CIAN.ru\n"
                    "- Auto.ru",
                    reply_markup=get_main_keyboard()
                )
                return
            
            # Запрашиваем имя для отслеживания
            logger.info("Запрашиваем имя для отслеживания")
            context.user_data["waiting_for_name"] = True
            context.user_data["pending_url"] = url
            
            await update.message.reply_text(
                "📝 Пожалуйста, введите название для этого отслеживания (например, «Квартиры в центре» или «Машины до 1 млн»):",
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Общая ошибка в handle_url: {e}")
        logger.exception(e)
        await update.message.reply_text(
            "❌ Произошла неожиданная ошибка при обработке вашего запроса.\n"
            "Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
            reply_markup=get_main_keyboard()
        )
async def handle_url_with_state(update: Update, context: ContextTypes.DEFAULT_TYPE, quick_response=None) -> None:
    """Неблокирующая версия обработки URL"""
    try:
        BOT_STATE["parsing_tasks"] += 1
        
        # Основная логика обработки URL
        await handle_url(update, context, quick_response)
        
    finally:
        BOT_STATE["parsing_tasks"] -= 1

# Асинхронная версия сохранения данных
async def save_data_async():
    """Асинхронная версия функции сохранения данных"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, save_data)

# Функция очистки устаревших данных
async def cleanup_data_job(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневно очищает устаревшие данные для экономии места на сервере"""
    logger.info("Запуск процедуры очистки устаревших данных...")
    
    try:
        # Получаем текущую дату
        current_time = datetime.now()
        
        # Очистка истекших подписок старше 30 дней
        expired_subscriptions = []
        for user_id, sub_data in subscriptions.items():
            if not sub_data.get("active", False) and "expiry_date" in sub_data:
                expiry_date = datetime.fromisoformat(sub_data["expiry_date"])
                days_since_expiry = (current_time - expiry_date).days
                
                if days_since_expiry > 30:  # Оставляем неактивные подписки в базе только на 30 дней
                    expired_subscriptions.append(user_id)
        
        # Удаляем истекшие подписки
        for user_id in expired_subscriptions:
            logger.info(f"Удаление истекшей подписки пользователя {user_id}")
            if user_id in subscriptions:
                del subscriptions[user_id]
        
        # Очистка неактивных отслеживаний
        removed_trackings = 0
        for user_id in list(user_data.keys()):
            if "jobs" in user_data[user_id]:
                # Очищаем отслеживания без URL
                empty_jobs = [job_id for job_id, job_info in user_data[user_id]["jobs"].items() 
                              if "url" not in job_info or not job_info["url"]]
                
                for job_id in empty_jobs:
                    logger.info(f"Удаление пустого отслеживания {job_id} пользователя {user_id}")
                    del user_data[user_id]["jobs"][job_id]
                    removed_trackings += 1
                
                # Удаляем отслеживания с истекшей датой более 7 дней назад
                expired_jobs = []
                for job_id, job_info in user_data[user_id]["jobs"].items():
                    if "expiry_date" in job_info:
                        try:
                            expiry_date = datetime.fromisoformat(job_info["expiry_date"])
                            days_since_expiry = (current_time - expiry_date).days
                            
                            if days_since_expiry > 7:  # Отслеживания удаляем через 7 дней после истечения
                                expired_jobs.append(job_id)
                        except:
                            pass
                
                for job_id in expired_jobs:
                    logger.info(f"Удаление истекшего отслеживания {job_id} пользователя {user_id}")
                    del user_data[user_id]["jobs"][job_id]
                    removed_trackings += 1
                
                # Если у пользователя не осталось отслеживаний и нет активной подписки, удаляем его данные
                if not user_data[user_id]["jobs"] and (user_id not in subscriptions or not subscriptions[user_id].get("active", False)):
                    logger.info(f"Удаление данных неактивного пользователя {user_id}")
                    del user_data[user_id]
        
        # Очистка платежей старше 90 дней
        if "payments" in payments:
            current_payments = payments["payments"]
            old_payments = []
            
            for payment_id, payment_info in current_payments.items():
                if "created_at" in payment_info:
                    try:
                        created_at = datetime.fromisoformat(payment_info["created_at"])
                        days_since_creation = (current_time - created_at).days
                        
                        if days_since_creation > 90:  # Сохраняем историю платежей на 90 дней
                            old_payments.append(payment_id)
                    except:
                        pass
            
            # Удаляем старые платежи
            for payment_id in old_payments:
                logger.info(f"Удаление старого платежа {payment_id}")
                del payments["payments"][payment_id]
        
        # Ограничиваем размер хранимых ID объявлений
        for user_id in user_data:
            if "jobs" in user_data[user_id]:
                for job_id in user_data[user_id]["jobs"]:
                    if "seen_ids" in user_data[user_id]["jobs"][job_id]:
                        # Оставляем только последние 1000 ID для каждого отслеживания
                        user_data[user_id]["jobs"][job_id]["seen_ids"] = user_data[user_id]["jobs"][job_id]["seen_ids"][-1000:]
        
        # Сохраняем обновленные данные
        save_data()
        
        # Выводим отчет о выполненной очистке
        logger.info(f"Очистка данных завершена. Удалено подписок: {len(expired_subscriptions)}, "
                   f"отслеживаний: {removed_trackings}, платежей: {len(old_payments) if 'old_payments' in locals() else 0}")
        
        # Дополнительно делаем резервную копию данных раз в день
        try:
            # Создаем папку для бэкапов, если она еще не существует
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # Форматирование текущей даты для имени файла
            date_str = current_time.strftime("%Y%m%d")
            
            # Копируем файлы данных с датой в имени
            import shutil
            shutil.copy2(DATA_FILE, f"{backup_dir}/{date_str}_{DATA_FILE}")
            shutil.copy2(SUBSCRIPTIONS_FILE, f"{backup_dir}/{date_str}_{SUBSCRIPTIONS_FILE}")
            shutil.copy2(PAYMENTS_FILE, f"{backup_dir}/{date_str}_{PAYMENTS_FILE}")
            
            logger.info(f"Создана резервная копия данных с датой {date_str}")
            
            # Удаляем старые бэкапы (оставляем только за последние 7 дней)
            import glob
            all_backups = glob.glob(f"{backup_dir}/*_{DATA_FILE}")
            all_backups.sort()
            
            if len(all_backups) > 7:
                for old_backup in all_backups[:-7]:
                    os.remove(old_backup)
                    logger.info(f"Удален старый бэкап {old_backup}")
                
                # Также удаляем соответствующие бэкапы других файлов
                for backup_file in all_backups[:-7]:
                    backup_date = os.path.basename(backup_file).split('_')[0]
                    sub_backup = f"{backup_dir}/{backup_date}_{SUBSCRIPTIONS_FILE}"
                    pay_backup = f"{backup_dir}/{backup_date}_{PAYMENTS_FILE}"
                    
                    if os.path.exists(sub_backup):
                        os.remove(sub_backup)
                    if os.path.exists(pay_backup):
                        os.remove(pay_backup)
            
        except Exception as backup_error:
            logger.error(f"Ошибка при создании резервной копии: {backup_error}")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке данных: {e}")
        logger.exception(e)

async def handle_url_with_state(update: Update, context: ContextTypes.DEFAULT_TYPE, quick_response=None) -> None:
    """Неблокирующая версия обработки URL"""
    try:
        BOT_STATE["parsing_tasks"] += 1
        
        # Основная логика обработки URL
        await handle_url(update, context, quick_response)
        
    finally:
        BOT_STATE["parsing_tasks"] -= 1

# Функция для обработки обычных текстовых сообщений (кнопки меню)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает обычные текстовые сообщения с приоритизацией"""
    # Устанавливаем флаг обработки команды
    BOT_STATE["processing_command"] = True
    
    try:
        text = update.message.text
        
        # Проверяем, ожидает ли бот имя для ссылки
        if context.user_data.get("waiting_for_name", False):
            logger.info(f"Получено имя для отслеживания: {text}")
            
            # Сохраняем имя и получаем сохраненную ссылку
            context.user_data["tracking_name"] = text
            
            # Запускаем продолжение добавления ссылки с сохраненным именем
            quick_response = await update.message.reply_text(
                f"📝 Получил название: '{text}'\n⏳ Добавляю отслеживание...",
                reply_markup=get_main_keyboard()
            )
            
            # Продолжаем обработку с сохраненной ссылкой
            asyncio.create_task(
                handle_url_with_state(update, context, quick_response)
            )
            return
        
        # Обработка меню и команд    
        if text == "🔍 Мои отслеживания":
            await list_tracking(update, context)
        elif text == "💳 Подписка":
            await subscription_info(update, context)
        elif text == "📚 Инструкция":
            await instruction_command(update, context)
        elif text == "❓ Помощь":
            await help_command(update, context)
        else:
            # Для других сообщений проверяем, содержит ли оно URL
            url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
            if url_pattern.search(text):
                # Если содержит URL, обрабатываем как ссылку
                # Отправляем быстрый ответ, а парсинг запустим отдельно
                quick_response = await update.message.reply_text(
                    "⏳ Получил вашу ссылку, анализирую...",
                    reply_markup=get_main_keyboard()
                )
                
                # Запускаем обработку URL асинхронно, чтобы не блокировать бота
                asyncio.create_task(
                    handle_url_with_state(update, context, quick_response)
                )
                return
            else:
                # Проверяем, может ли это быть названием для ссылки, ожидающей название
                if context.user_data.get("waiting_for_name", False):
                    logger.info(f"Получено название для отслеживания (вторая проверка): {text}")
                    context.user_data["tracking_name"] = text
                    quick_response = await update.message.reply_text(
                        f"📝 Получил название: '{text}'\n⏳ Добавляю отслеживание...",
                        reply_markup=get_main_keyboard()
                    )
                    asyncio.create_task(
                        handle_url_with_state(update, context, quick_response)
                    )
                    return
                else:
                    # Иначе отправляем сообщение с подсказкой
                    await update.message.reply_text(
                        "🤔 Не понимаю ваше сообщение.\n\n"
                        "📌 Чтобы добавить отслеживание, отправьте ссылку на поиск с Avito, ЦИАН или Auto.ru.\n"
                        "📌 Для управления используйте кнопки меню или команды.",
                        reply_markup=get_main_keyboard()
                    )
    finally:
        # Сбрасываем флаг обработки команды
        BOT_STATE["processing_command"] = False
# Функция для обработки запросов от callback_query
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все callback_query"""
    query = update.callback_query
    
    if query.data.startswith("sub_") or query.data.startswith("pay_") or query.data.startswith("cancel_"):
        await subscription_callback(update, context)
    elif query.data.startswith("stop_"):
        await stop_tracking_callback(update, context)
    elif query.data == "show_subscription_plans":
        await query.answer()
        await query.message.reply_text(
            "💳 Выберите тариф подписки:",
            reply_markup=get_subscription_keyboard()
        )
    elif query.data == "extend_subscription" or query.data == "upgrade_subscription":
        await subscription_callback(update, context)

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки"""
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка при выполнении операции. "
            "Пожалуйста, попробуйте позже или обратитесь к @sergeewich9 за помощью.",
            reply_markup=get_main_keyboard()
        )

# === ФУНКЦИИ АДМИНКИ ===

# Проверка, является ли пользователь администратором
def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# Обработчик команды администратора для просмотра статистики
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику использования бота (только для админа)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    # Собираем статистику
    total_users = len(user_data)
    total_subscriptions = len(subscriptions)
    active_subscriptions = sum(1 for sub in subscriptions.values() if sub.get("active", False))
    total_trackings = sum(len(user_data.get(u, {}).get("jobs", {})) for u in user_data)
    
    # Статистика по планам подписок
    plans_stats = {}
    for plan in SUBSCRIPTION_PLANS:
        plans_stats[plan] = 0
    
    for sub in subscriptions.values():
        if sub.get("active", False) and "plan" in sub:
            plans_stats[sub["plan"]] = plans_stats.get(sub["plan"], 0) + 1
    
    # Статистика по платежам
    total_payments = len(payments.get("payments", {}))
    completed_payments = sum(1 for p in payments.get("payments", {}).values() if p.get("status") == "completed")
    total_income = sum(p.get("amount", 0) for p in payments.get("payments", {}).values() if p.get("status") == "completed")
    
    # Статистика по сайтам
    sites_stats = {"avito": 0, "cian": 0, "auto": 0}
    for u in user_data:
        for job in user_data.get(u, {}).get("jobs", {}).values():
            site_type = job.get("site_type")
            if site_type in sites_stats:
                sites_stats[site_type] += 1
    
    # Формируем сообщение
    message = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💳 Всего подписок: {total_subscriptions}\n"
        f"✅ Активных подписок: {active_subscriptions}\n"
        f"🔍 Всего отслеживаний: {total_trackings}\n\n"
        
        f"<b>Статистика по тарифам:</b>\n"
        f"🔹 Пробный: {plans_stats.get('trial', 0)}\n"
        f"🔷 Неделя: {plans_stats.get('week', 0)}\n"
        f"⭐ Месяц: {plans_stats.get('month', 0)}\n\n"
        
        f"<b>Статистика по сайтам:</b>\n"
        f"🟢 Avito: {sites_stats.get('avito', 0)}\n"
        f"🔵 ЦИАН: {sites_stats.get('cian', 0)}\n"
        f"🔴 Auto.ru: {sites_stats.get('auto', 0)}\n\n"
        
        f"<b>Финансы:</b>\n"
        f"💰 Всего платежей: {total_payments}\n"
        f"✅ Успешных платежей: {completed_payments}\n"
        f"💵 Общий доход: {total_income} ₽"
    )
    
    # Кнопки для админа
    keyboard = [
        [InlineKeyboardButton("📋 Список активных пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("💳 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("🔄 Обновить статистику", callback_data="admin_refresh_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

# Обработчик для управления пользователями (админка)
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список пользователей бота (только для админа)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    # Собираем информацию о пользователях
    users_info = []
    
    for u_id in user_data:
        # Базовая информация
        user_info = {
            "id": u_id,
            "jobs_count": len(user_data.get(u_id, {}).get("jobs", {})),
            "has_subscription": u_id in subscriptions,
            "active_subscription": subscriptions.get(u_id, {}).get("active", False),
            "plan": subscriptions.get(u_id, {}).get("plan", "Нет"),
            "expiry_date": subscriptions.get(u_id, {}).get("expiry_date", "Нет")
        }
        
        users_info.append(user_info)
    
    # Сортируем по наличию активной подписки
    users_info.sort(key=lambda x: (not x["active_subscription"], not x["has_subscription"]))
    
    if not users_info:
        await update.message.reply_text("👥 Пользователей пока нет.")
        return
    
    # Формируем сообщение с первыми 10 пользователями
    message = "👥 <b>Список пользователей бота:</b>\n\n"
    
    for i, user in enumerate(users_info[:10], 1):
        sub_status = "✅ Активна" if user["active_subscription"] else "❌ Неактивна"
        expiry = "Нет"
        if user["expiry_date"] != "Нет":
            try:
                expiry_date = datetime.fromisoformat(user["expiry_date"])
                expiry = expiry_date.strftime("%d.%m.%Y")
            except:
                pass
        
        message += (
            f"{i}. ID: {user['id']}\n"
            f"   Отслеживаний: {user['jobs_count']}\n"
            f"   Подписка: {sub_status} ({user['plan']})\n"
            f"   Истекает: {expiry}\n\n"
        )
    
    # Добавляем навигационные кнопки
    keyboard = []
    
    if len(users_info) > 10:
        keyboard.append([InlineKeyboardButton("➡️ Следующая страница", callback_data="admin_users_page_2")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back_to_stats")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

# Обработчик для управления подписками (админка)
async def admin_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Управление подписками пользователей (только для админа)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    # Получаем активные подписки
    active_subs = []
    
    for u_id, sub_data in subscriptions.items():
        if sub_data.get("active", False):
            try:
                expiry_date = datetime.fromisoformat(sub_data["expiry_date"])
                days_left = (expiry_date - datetime.now()).days
                
                active_subs.append({
                    "user_id": u_id,
                    "plan": sub_data["plan"],
                    "expiry_date": expiry_date,
                    "days_left": days_left
                })
            except:
                continue
    
    # Сортируем по дате истечения
    active_subs.sort(key=lambda x: x["days_left"])
    
    if not active_subs:
        await update.message.reply_text("💳 Активных подписок пока нет.")
        return
    
    # Формируем сообщение с первыми 10 подписками
    message = "💳 <b>Активные подписки пользователей:</b>\n\n"
    
    for i, sub in enumerate(active_subs[:10], 1):
        plan_name = SUBSCRIPTION_PLANS[sub["plan"]]["name"]
        expiry = sub["expiry_date"].strftime("%d.%m.%Y")
        
        message += (
            f"{i}. ID пользователя: {sub['user_id']}\n"
            f"   Тариф: {plan_name}\n"
            f"   Истекает: {expiry}\n"
            f"   Осталось дней: {sub['days_left']}\n\n"
        )
    
    # Кнопки для управления
    keyboard = []
    
    if len(active_subs) > 10:
        keyboard.append([InlineKeyboardButton("➡️ Следующая страница", callback_data="admin_subs_page_2")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить подписку", callback_data="admin_add_sub")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back_to_stats")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

# Обработчик для добавления подписки пользователю (админка)
async def admin_add_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает ID пользователя для добавления подписки (только для админа)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔ У вас нет доступа к этой функции.")
        return
    
    # Запрашиваем ID пользователя
    await query.edit_message_text(
        "➕ <b>Добавление подписки пользователю</b>\n\n"
        "Введите команду в формате:\n"
        "/add_sub ID_ПОЛЬЗОВАТЕЛЯ ПЛАН ДНЕЙ\n\n"
        "Например:\n"
        "/add_sub 123456789 month 30\n\n"
        "Доступные планы: trial, week, month",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="admin_back_to_subscriptions")
        ]])
    )

# Обработчик команды добавления подписки
async def add_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавляет подписку указанному пользователю (только для админа)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ Неверный формат команды.\n"
            "Используйте: /add_sub ID_ПОЛЬЗОВАТЕЛЯ ПЛАН ДНЕЙ\n"
            "Например: /add_sub 123456789 month 30"
        )
        return
    
    try:
        target_user_id = context.args[0]
        plan = context.args[1]
        days = int(context.args[2])
        
        if plan not in SUBSCRIPTION_PLANS:
            await update.message.reply_text(
                f"⚠️ Неверный план подписки: {plan}\n"
                "Доступные планы: trial, week, month"
            )
            return
        
        # Добавляем или обновляем подписку
        start_date = datetime.now()
        expiry_date = start_date + timedelta(days=days)
        
        subscriptions[target_user_id] = {
            "active": True,
            "plan": plan,
            "start_date": start_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "added_by_admin": True
        }
        
        save_data()
        
        # Уведомляем админа
        await update.message.reply_text(
            f"✅ Подписка успешно добавлена пользователю {target_user_id}:\n"
            f"📋 План: {SUBSCRIPTION_PLANS[plan]['name']}\n"
            f"📅 Срок действия: {days} дней (до {expiry_date.strftime('%d.%m.%Y')})"
        )
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=int(target_user_id),
                text=(
                    "🎁 Вам активирована подписка администратором!\n\n"
                    f"📋 Тариф: {SUBSCRIPTION_PLANS[plan]['name']}\n"
                    f"📅 Срок действия: {days} дней (до {expiry_date.strftime('%d.%m.%Y')})\n"
                    f"🔍 Доступно отслеживаний: {SUBSCRIPTION_PLANS[plan]['max_urls']}\n\n"
                    "Теперь вы можете добавлять ссылки для отслеживания."
                )
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {target_user_id}: {e}")
            await update.message.reply_text(
                f"⚠️ Подписка добавлена, но не удалось отправить уведомление пользователю: {e}"
            )
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# Обработчик для колбэков админки
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает callback_query для админских функций"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔ У вас нет доступа к этой функции.")
        return
    
    callback_data = query.data
    
    if callback_data == "admin_refresh_stats":
        # Обновляем статистику
        await admin_stats(update, context)
    
    elif callback_data == "admin_users":
        # Список пользователей
        await admin_users(update, context)
    
    elif callback_data == "admin_subscriptions":
        # Управление подписками
        await admin_subscriptions(update, context)
    
    elif callback_data == "admin_back_to_stats":
        # Возврат к статистике
        await admin_stats(update, context)
    
    elif callback_data == "admin_back_to_subscriptions":
        # Возврат к списку подписок
        await admin_subscriptions(update, context)
    
    elif callback_data == "admin_add_sub":
        # Добавление подписки
        await admin_add_subscription(update, context)
    
    elif callback_data.startswith("admin_users_page_"):
        # Пагинация списка пользователей
        page = int(callback_data.split("_")[-1])
        
        # Тут будет логика для отображения нужной страницы пользователей
        # Для прототипа можно упростить
        await query.edit_message_text(
            f"📄 Страница {page} списка пользователей.\n"
            "Эта функция находится в разработке.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="admin_users")
            ]])
        )
    
    elif callback_data.startswith("admin_subs_page_"):
        # Пагинация списка подписок
        page = int(callback_data.split("_")[-1])
        
        # Тут будет логика для отображения нужной страницы подписок
        # Для прототипа можно упростить
        await query.edit_message_text(
            f"📄 Страница {page} списка подписок.\n"
            "Эта функция находится в разработке.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="admin_subscriptions")
            ]])
        )

# Вспомогательная функция для регулярной проверки и обновления состояния подписок
async def check_subscriptions_job(context: ContextTypes.DEFAULT_TYPE):
    """Регулярно проверяет подписки и обновляет их статус"""
    logger.info("Запуск проверки подписок...")
    check_subscriptions()
    logger.info("Проверка подписок завершена")

async def download_image(url):
    """Скачивает изображение по URL с повторными попытками"""
    max_retries = 3
    retry_delay = 1
    
    # Проверка и исправление URL
    if not url:
        logger.error("Пустой URL изображения")
        return None
    
    # Исправляем URL если он в формате data-marker
    if url.startswith('slider-image/image-'):
        url = url.replace('slider-image/image-', '')
    
    # Исправляем относительные URL
    if url.startswith('//'):
        url = f'https:{url}'
    
    logger.info(f"Скачиваем изображение: {url}")
    
    # Добавляем случайную задержку перед скачиванием
    await asyncio.sleep(random.uniform(1.0, 2.0))
    
    for attempt in range(max_retries):
        try:
            # Более реалистичные заголовки для скачивания изображений
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.avito.ru/',
                'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            # Используем обычные requests вместо асинхронных для совместимости
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"Ошибка при скачивании изображения: статус {response.status_code}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Увеличиваем задержку для следующей попытки
                continue
            
            # Проверяем, что контент - изображение
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('image/'):
                logger.info(f"Успешно скачано изображение: {url[:50]}...")
                return response.content
            else:
                logger.warning(f"Неверный тип контента: {content_type}")
        
        except Exception as e:
            logger.error(f"Ошибка при скачивании изображения (попытка {attempt+1}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
    
    logger.error(f"Не удалось скачать изображение после {max_retries} попыток: {url[:50]}...")
    return None

# Функция для получения подробной информации об объявлении Avito
# ПОСЛЕ:
async def get_avito_details(url):
    """Получает подробную информацию об объявлении Avito"""
    try:
        # Более реалистичные заголовки, похожие на настоящий браузер
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.avito.ru/',
            'Connection': 'keep-alive',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Добавляем задержку перед запросом, чтобы избежать блокировки
        await asyncio.sleep(random.uniform(1.5, 3.0))
        
        logger.info(f"Получение данных объявления Avito: {url}")
        
        # Используем сессию для сохранения cookies
        session = requests.Session()
        session.headers.update(headers)
        
        # Используем прокси при необходимости
        # Добавляем значительную задержку перед запросом
        delay = random.uniform(MIN_REQUEST_DELAY, MAX_REQUEST_DELAY)
        logger.info(f"Ожидание {delay:.2f} секунд перед запросом деталей объявления...")
        await asyncio.sleep(delay)

        response = session.get(url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при загрузке страницы объявления: статус {response.status_code}")
            return {}
        
        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлекаем данные
        details = {}
        
        
        # Изображения
        images = []
        # Новые селекторы для изображений Auto.ru с учетом скриншота
        gallery_items = (
            soup.select('div.OfferGallery__mainImage img') or 
            soup.select('div.ImageGallery__mainImage img') or 
            soup.select('div.ImageGalleryDesktop__image img') or
            soup.select('div[class*="listing-item"] img') or 
            soup.select('div[data-seo="listing-item"] img') or
            soup.select('div[class*="OfferThumb"] img[class*="IconSvg_img"]') or
            soup.select('svg[class*="IconSvg IconSvg_name"] image')
        )

        for img in gallery_items:
            src_attr = 'src'
            if img.name == 'svg' or 'xlink:href' in img.attrs:
                src_attr = 'xlink:href'
            
            if src_attr in img.attrs:
                img_url = img[src_attr]
                # Исправление относительных URL
                if img_url:
                    if img_url.startswith('//'):
                        img_url = f'https:{img_url}'
                    if img_url not in images:
                        images.append(img_url)
                        if len(images) >= 1:  # Берем только одну фотографию
                            break  # Берем только первое изображение
        
        # Если не нашли через слайдер, пробуем другие селекторы
        if not images:
            # Альтернативные селекторы для поиска изображений
            selectors = [
                'div[data-marker="item-view/gallery"] img',
                'div[data-marker="item-photo"] img',
                'div[class*="photo-slider"] img',
                'div[class*="gallery"] img'
            ]
            
            for selector in selectors:
                img_elements = soup.select(selector)
                if img_elements:
                    logger.info(f"Найдено изображений через селектор {selector}: {len(img_elements)}")
                    for img in img_elements:
                        if 'src' in img.attrs:
                            img_url = img['src']
                            # Проверяем, что это не заглушка и не иконка
                            if img_url and not img_url.endswith('.svg') and not img_url.endswith('.gif'):
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                images.append(img_url)
                                break  # Берем только первое изображение
                    if images:
                        break  # Выходим после первого успешного селектора
        
        # Название объявления
        title_elem = soup.select_one('h1[data-marker="item-view/title-info"]') or soup.select_one('h1.title-info-title')
        if title_elem:
            details['title'] = title_elem.get_text().strip()
        
        # Цена
        price_elem = soup.select_one('span[data-marker="item-view/item-price"]') or soup.select_one('span.js-item-price')
        if price_elem:
            price_text = price_elem.get_text().strip()
            # Очищаем цену от лишних символов
            details['price'] = re.sub(r'\s+', ' ', price_text)
        
        # Город
        location_elem = soup.select_one('div[data-marker="item-view/item-address"]') or soup.select_one('span.item-address__string')
        if location_elem:
            city_text = location_elem.get_text().strip()
            # Извлекаем город (обычно первая часть адреса)
            city_match = re.search(r'^([^,]+)', city_text)
            if city_match:
                details['city'] = city_match.group(1).strip()
            else:
                details['city'] = city_text
        
        # Продавец
        seller_elem = soup.select_one('div[data-marker="seller-info/name"]') or soup.select_one('div.seller-info-name')
        if seller_elem:
            details['seller_name'] = seller_elem.get_text().strip()
        
        # Рейтинг продавца
        rating_elem = soup.select_one('div[data-marker="seller-info/rating"]')
        if rating_elem:
            rating_text = rating_elem.get_text().strip()
            rating_match = re.search(r'(\d[,.]\d+)', rating_text)
            if rating_match:
                raw_rating = rating_match.group(1).replace(',', '.')
                try:
                    rating_value = float(raw_rating)
                    # Преобразуем рейтинг от 1 до 5 в звездочки
                    stars = int(round(rating_value))
                    details['seller_rating'] = '⭐' * stars
                except:
                    details['seller_rating'] = 'Нет данных'
            else:
                details['seller_rating'] = 'Нет данных'
        
        # Добавляем изображения
        details['images'] = images
        logger.info(f"Найдено изображений для объявления: {len(images)}")
        
        return details
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных объявления Avito: {e}")
        logger.exception(e)  # Выводим полный стек ошибки
        return {}

# Функция для получения подробной информации об объявлении ЦИАН
async def get_cian_details(url):
    """Получает подробную информацию об объявлении ЦИАН"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        logger.info(f"Получение данных объявления ЦИАН: {url}")
        session = requests.Session()
        # Сначала посещаем главную страницу для получения cookies
        session.get('https://cian.ru/', headers=headers, timeout=10)
        # Добавляем задержку
        time.sleep(random.uniform(1, 2))
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при загрузке страницы объявления ЦИАН: статус {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлекаем данные
        details = {}
        
        # Название объявления (для ЦИАН это обычно тип недвижимости и площадь)
        title_elem = soup.select_one('h1') or soup.select_one('h1.a10a3f92e9--title--UEEG3')
        if title_elem:
            details['title'] = title_elem.get_text().strip()
        
        # Цена
        price_elem = soup.select_one('span[itemprop="price"]') or soup.select_one('div.a10a3f92e9--amount--ON6i1')
        if price_elem:
            details['price'] = price_elem.get_text().strip()
        
        # Город
        address_elem = soup.select_one('div[data-name="AddressContainer"]') or soup.select_one('address.a10a3f92e9--address--F06X3')
        if address_elem:
            address_text = address_elem.get_text().strip()
            # Обычно город - первое слово в адресе
            city_match = re.search(r'^([^,]+)', address_text)
            if city_match:
                details['city'] = city_match.group(1).strip()
            else:
                details['city'] = 'Не указан'
        
        
        
        # Изображения с учетом скриншота ЦИАН
        images = []
        gallery_selectors = [
            'div.ImageGalleryDesktop__image img', 
            'div.Gallery__image img',
            'div[data-name="Gallery"] img',
            'img[src*="cian.ru/images"]',
            'img[src*="cdn-cian.ru/images"]',  # Новый селектор из скриншота
            'img[class*="_93444fe79c--container"]',
            'a[class*="_93444fe79c--media"] img',  # Новый селектор для блока медиа
            'img[data-name="GalleryImage"]'  # Возможный селектор для галереи
        ]

        # Перебираем все селекторы, пока не найдем изображения
        for selector in gallery_selectors:
            gallery_items = soup.select(selector)
            for img in gallery_items:
                if 'src' in img.attrs:
                    img_url = img['src']
                    # Исправление относительных URL
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = f'https:{img_url}'
                        if 'noimage' not in img_url.lower() and img_url not in images:
                            images.append(img_url)
                            
            # Если нашли хотя бы одно изображение, выходим из цикла
            if images:
                break

        # Проверяем наличие прямых ссылок на изображения в HTML
        if not images:
            img_urls = re.findall(r'https://images\.cdn-cian\.ru/images/[^"\']+', str(soup))
            if img_urls:
                images.extend(img_urls[:1])  # Добавляем первое найденное изображение
        
        details['images'] = images[:5]  # Первые 5 изображений
        
        return details
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных объявления ЦИАН: {e}")
        logger.exception(e)
        return {}

# Функция для получения подробной информации об объявлении Auto.ru
# Функция для получения подробной информации об объявлении Auto.ru
async def get_auto_details(url):
    """Получает подробную информацию об объявлении Auto.ru"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        logger.info(f"Получение данных объявления Auto.ru: {url}")
        session = requests.Session()
        # Сначала посещаем главную страницу для получения cookies
        session.get('https://auto.ru/', headers=headers, timeout=10)
        # Добавляем задержку
        time.sleep(random.uniform(1, 2))
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при загрузке страницы объявления Auto.ru: статус {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлекаем данные
        details = {}
        
        # Название объявления с поддержкой мобильной версии
        title_selectors = [
            'h1.CardHead__title',
            'h1.CarouselLayout__title',
            'div.ListingAmpItemHeader_title',  # Из скриншотов для мобильной версии
            'h3.ListingAmpItemHeader_title',
            'div.ListingAmpItemHeader_clicker',  # Дополнительный селектор для заголовка
            'a.AmpLink.ListingAmpItemHeader_titleLink'  # Из скриншотов - ссылка с названием
        ]

        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title_text = title_elem.get_text().strip()
                if title_text:
                    details['title'] = title_text
                    break

        # Дополнительная проверка на случай, если заголовок не найден
        if 'title' not in details:
            # Ищем текст заголовка в любом месте страницы, где может быть указана модель
            bmw_model_pattern = re.search(r'BMW (\d) серии .*? \(\w+\)', str(soup))
            if bmw_model_pattern:
                details['title'] = bmw_model_pattern.group(0)
        
        # Цена
        price_selectors = [
            'span.OfferPriceCaption__price',
            'div.Price__value',
            'div.ListingAmpItemHeader_price',  # Из скриншотов для мобильной версии
            '.ListingItemPrice__content'  # Общий селектор для цены
        ]

        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                if price_text:
                    details['price'] = price_text
                    break

        # Получаем URL объявления для мобильной и десктопной версии
        item_url = ""

        # Сначала пробуем найти ссылку из заголовка
        url_selectors = [
            'a.AmpLink.ListingAmpItemHeader_titleLink',
            'a.AmpLink[href*="/amp/cars/used/sale/bmw/"]',
            'a.Link[href*="/cars/used/sale/bmw/"]'
        ]

        for selector in url_selectors:
            url_element = soup.select_one(selector)
            if url_element and 'href' in url_element.attrs:
                item_url = url_element['href']
                
                # Обработка относительных URL
                if item_url.startswith('/'):
                    item_url = f"https://auto.ru{item_url}"
                break

        # Если ссылка все еще не найдена, извлекаем из текущего URL
        if not item_url:
            # Для мобильной версии Auto.ru, конвертируем AMP URL в обычный
            if url.startswith('https://auto.ru/amp/cars/'):
                item_url = url.replace('/amp/cars/', '/cars/')
            else:
                item_url = url

        # Убеждаемся, что ссылка абсолютная
        if item_url and not item_url.startswith('http'):
            item_url = f"https://auto.ru{item_url}"
            
        details['url'] = item_url
        
        # Изображения с улучшенными селекторами для Auto.ru на основе новых скриншотов
        images = []
        gallery_selectors = [
            'div.OfferGallery__mainImage img', 
            'div.ImageGallery__mainImage img',
            'div.ImageGalleryDesktop__image img',
            'img.IconSvg_img',
            'svg.IconSvg image',
            'div[data-seo="listing-item"] img',
            'a.Link.OfferThumb img',
            'a[class="Link OfferThumb OfferThumb_radius_8"] img',
            'div.ListingItem__thumb img',
            # Новые селекторы из скриншотов
            'amp-img[src*="avatars.mds.yandex.net"]',  # Селектор из скриншота мобильной версии
            'div.ListingAmpItemGallery img',  # Селектор галереи на мобильной странице
            'div.ListingAmpItemGallery_item img',
            'div.ListingAmpItemGallery_item amp-img'   # Селектор для AMP-страниц
        ]

        # Проверяем каждый селектор и ищем изображения
        for selector in gallery_selectors:
            items = soup.select(selector)
            for img in items:
                # Проверяем различные атрибуты, где может храниться URL изображения
                src_attrs = ['src', 'data-src', 'srcset']
                
                for src_attr in src_attrs:
                    if src_attr in img.attrs:
                        img_url = img[src_attr]
                        # Для srcset берем первый URL из списка
                        if src_attr == 'srcset':
                            img_url = img_url.split(' ')[0]
                        
                        # Обработка URL из AMP-страниц (из второго скриншота)
                        if "avatars.mds.yandex.net" in img_url:
                            # Исправление URL для скачивания
                            img_url = img_url.split(' ')[0].strip()
                            if img_url.startswith('//'):
                                img_url = f'https:{img_url}'
                            images.append(img_url)
                            break  # Найдено изображение, выходим из цикла
                            
                # Если изображение найдено, прекращаем поиск
                if images:
                    break
                    
            # Если изображение найдено после перебора всех элементов с текущим селектором, прекращаем поиск
            if images:
                break
        
        # Проверяем URL страницы для получения ID объявления, если изображения не найдены
        if not images:
            car_id_match = re.search(r'/sale/(\w+)-(\w+)', url)
            if car_id_match:
                car_id = car_id_match.group(1)
                photo_url = f"https://avatars.mds.yandex.net/get-autoru-vos/5413404/{car_id}_1200x900.jpg"
                images.append(photo_url)
        
        details['images'] = images
        
        return details
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных объявления Auto.ru: {e}")
        logger.exception(e)
        return {}

async def test_listings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тестовая команда для проверки выгрузки объявлений с трех площадок"""
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Начинаю тестовую выгрузку объявлений со всех площадок...")
    
    # Тестовые URL для каждой платформы
    test_urls = {
        "avito": "https://www.avito.ru/moskva/telefony/iphone_12_128_gb-ASgBAgICAUSwApitAaQKxK0D",
        "cian": "https://www.cian.ru/rent/flat/287577525/",
        "auto": "https://auto.ru/cars/used/sale/bmw/x3/1126609469-6c8d1e2b/"
    }
    
    results = {}
    
    # Параллельное выполнение запросов через asyncio.gather
    async def fetch_site_data(site_name, url):
        await update.message.reply_text(f"⏳ Получаю данные с {site_name.upper()}...")
        results[site_name] = fetch_listings(url)
        return site_name, results[site_name]
    
    # Запускаем задачи параллельно
    tasks = [fetch_site_data(site, url) for site, url in test_urls.items()]
    site_results = await asyncio.gather(*tasks)
    
    for site_name, site_listings in site_results:
        if site_listings and len(site_listings) > 0:
            await update.message.reply_text(f"✅ Получены объявления с {site_name.upper()} ({len(site_listings)})")
            
            # Отправляем первое объявление для примера
            listing = site_listings[0]
            await send_listing_with_button(context.bot, user_id, listing)
        else:
            await update.message.reply_text(f"❌ Не удалось получить объявления с {site_name.upper()}")
    
    await update.message.reply_text("✅ Тестовая выгрузка завершена!")

async def rotate_proxy_job(context: ContextTypes.DEFAULT_TYPE):
    """Регулярно выполняет ротацию IP прокси"""
    global PROXY_ERROR_COUNT
    
    active_tasks = BOT_STATE.get("parsing_tasks", 0)
    if active_tasks > 0:
        logger.info(f"Пропуск плановой ротации IP: выполняется {active_tasks} активных задач парсинга")
        return
        
    logger.info("Запланированная ротация IP прокси...")
    PROXY_ERROR_COUNT = 0
    success = rotate_proxy_ip(force=True)
    logger.info(f"Ротация IP прокси: {'успешно' if success else 'ошибка'}")
    
    # Уменьшаем задержку после ротации
    await asyncio.sleep(3)  # Вместо 5


# Универсальная функция получения подробной информации об объявлении
async def get_listing_details(url, site_type):
    """Получает подробную информацию об объявлении в зависимости от типа сайта"""
    if site_type == "avito":
        return await get_avito_details(url)
    elif site_type == "cian":
        return await get_cian_details(url)
    elif site_type == "auto":
        return await get_auto_details(url)
    else:
        logger.error(f"Неподдерживаемый тип сайта для URL: {url}")
        return {}

def main() -> None:
    """Запускает бота"""
    try:
        # Загружаем сохраненные данные
        load_data()
        logger.info("Данные загружены успешно")
        
        # Тестируем доступ к Авито
        logger.info("Выполняю тестовый запрос к Авито...")
        avito_test_result = fetch_avito_listings("https://www.avito.ru/moskva/kvartiry/prodam-ASgBAgICAUSSA8YQ")
        logger.info(f"Тестовый запрос к Авито: получено {len(avito_test_result)} объявлений")
        if avito_test_result:
            logger.info(f"Пример объявления: ID={avito_test_result[0]['id']}, Заголовок={avito_test_result[0]['title']}")
        logger.info(f"Тест доступа к Авито: {'УСПЕШНО' if avito_test_result else 'НЕУДАЧНО'}")
        
        # Тест изображений без создания отдельного event loop
        try:
            # Используем run в синхронном контексте
            image_test_result = asyncio.run(test_avito_images())
            logger.info(f"Тест загрузки изображений с Авито: {'УСПЕШНО' if image_test_result else 'НЕУДАЧНО'}")
        except Exception as img_error:
            logger.error(f"Ошибка при тесте изображений: {img_error}")
            image_test_result = False
        
        # Создаем приложение с явной проверкой инициализации
        logger.info("Создание приложения...")
        application = Application.builder().token(TOKEN).build()
        logger.info("Приложение создано")
        
        # Проверяем наличие job_queue
        if not hasattr(application, 'job_queue') or application.job_queue is None:
            try:
                from telegram.ext import JobQueue
                logger.warning("❌ job_queue не инициализирован в приложении! Попытка вручную создать JobQueue.")
                
                # Создаем вручную job_queue и привязываем к application
                job_queue = JobQueue()
                job_queue.set_application(application)
                application.job_queue = job_queue
                job_queue.start()
                logger.info("✅ job_queue создан вручную и успешно инициализирован")
            except Exception as e:
                logger.error(f"❌ Не удалось вручную создать job_queue: {e}")
                logger.error("Планировщик задач не будет работать. Используйте ручные проверки через /check")
        else:
            # Проверка функциональности job_queue через тестовую задачу
            try:
                def test_job(context):
                    logger.info("Тестовое задание job_queue выполнено успешно")
                
                application.job_queue.run_once(test_job, 5)
                logger.info("✅ job_queue инициализирован успешно и работает")
            except Exception as e:
                logger.error(f"❌ job_queue инициализирован, но не функционирует: {e}")
        
        # Добавляем обработчики команд
        logger.info("Добавление обработчиков команд...")
        # Добавляем существующие обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("list", list_tracking))
        application.add_handler(CommandHandler("stop", stop_tracking))
        application.add_handler(CommandHandler("subscription", subscription_info))
        application.add_handler(CommandHandler("check", manual_check))
        application.add_handler(CommandHandler("test", test_listings_command))  # Новая команда
        
        # Обработчики для админки
        application.add_handler(CommandHandler("admin", admin_stats))
        application.add_handler(CommandHandler("add_sub", add_subscription_command))
        
        # Обработчик для инлайн-кнопок
        application.add_handler(CallbackQueryHandler(callback_handler))
        
        # Обработчик для URL и обычных сообщений
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        ))
        logger.info("Обработчики команд добавлены")
        
        # Регистрируем обработчик ошибок
        application.add_error_handler(error_handler)
        logger.info("Обработчик ошибок зарегистрирован")
        
        # Пробуем добавить регулярные задачи через job_queue
        try:
            if hasattr(application, 'job_queue') and application.job_queue:
                # Проверка подписок (раз в час)
                application.job_queue.run_repeating(
                    check_subscriptions_job,
                    interval=3600,  # Проверка раз в час
                    first=60  # Первая проверка через минуту после запуска
                )
                logger.info("Регулярная проверка подписок добавлена в планировщик")
                
                # Очистка данных (раз в день в 3:00 ночи)
                application.job_queue.run_daily(
                    cleanup_data_job,
                    time=datetime.time(hour=3, minute=0),  # Запуск в 3:00
                    days=(0, 1, 2, 3, 4, 5, 6)  # Запуск каждый день недели
                )
                logger.info("Регулярная очистка данных добавлена в планировщик (запуск в 03:00)")
                
                # Ротация IP прокси (интервал из настроек)
                application.job_queue.run_repeating(
                    rotate_proxy_job,
                    interval=PROXY_SETTINGS['rotation_minutes'] * 60,  # перевод минут в секунды
                    first=120  # Первая ротация через 2 минуты после запуска
                )
                logger.info(f"Задача ротации IP добавлена в планировщик (каждые {PROXY_SETTINGS['rotation_minutes']} мин)")
            else:
                logger.warning("Невозможно добавить регулярные задачи: job_queue недоступен")
        except Exception as e:
            logger.error(f"Ошибка при добавлении регулярных задач: {e}")
        
        # Восстанавливаем задачи мониторинга из сохраненных данных
        logger.info("Восстановление сохраненных задач мониторинга...")
        restored_count = 0
        
        for user_id_str, user_info in user_data.items():
            if "jobs" in user_info:
                user_id = int(user_id_str)
                
                # Проверяем наличие активной подписки
                has_subscription = (user_id_str in subscriptions and subscriptions[user_id_str].get("active", False))
                
                if has_subscription:
                    # Получаем план подписки
                    plan = subscriptions[user_id_str]["plan"]
                    # Проверка на существование плана в новой структуре
                    if plan not in SUBSCRIPTION_PLANS:
                        logger.warning(f"План {plan} не найден в текущей конфигурации. Используем простой план.")
                        plan = "simple"
                        subscriptions[user_id_str]["plan"] = "simple"  # Обновляем план на существующий
                        save_data()  # Сохраняем изменения
                    base_interval = SUBSCRIPTION_PLANS[plan]["interval"]
                    
                    for job_name, job_info in user_info["jobs"].items():
                        url = job_info.get("url")
                        site_type = job_info.get("site_type", "")
                        
                        if url:
                            # Определяем интервал в зависимости от сайта
                            if site_type == "auto":
                                actual_interval = min(base_interval, AUTO_RU_INTERVAL)
                            elif site_type == "cian":
                                actual_interval = min(base_interval, CIAN_INTERVAL)
                            else:
                                actual_interval = min(base_interval, DEFAULT_CHECK_INTERVAL)

                            # Добавляем случайность к интервалу
                            actual_interval += random.randint(-RANDOM_DELAY_FACTOR, RANDOM_DELAY_FACTOR)
                            
                            # Гарантируем минимальный интервал
                            actual_interval = max(actual_interval, 30)
                            
                            # Пробуем добавить задачу в планировщик
                            try:
                                if hasattr(application, 'job_queue') and application.job_queue:
                                    # Удаляем существующие задачи с таким же именем
                                    for job in application.job_queue.get_jobs_by_name(job_name):
                                        job.schedule_removal()
                                    
                                    # Добавляем новую задачу
                                    application.job_queue.run_repeating(
                                        check_listings,
                                        interval=actual_interval,
                                        first=random.randint(10, 60),  # Рандомная начальная задержка
                                        name=job_name,
                                        data={
                                            'user_id': user_id,
                                            'url': url,
                                            'job_name': job_name
                                        }
                                    )
                                    restored_count += 1
                                    logger.info(f"Восстановлена задача {job_name} для пользователя {user_id} с интервалом {actual_interval} сек")
                                else:
                                    logger.warning(f"Пропуск задачи {job_name}: job_queue недоступен")
                                    # Отмечаем для ручной проверки
                                    user_data[user_id_str]["manual_check"] = True
                            except Exception as e:
                                logger.error(f"Ошибка при восстановлении задачи {job_name}: {e}")
                                # Отмечаем для ручной проверки
                                user_data[user_id_str]["manual_check"] = True
        
        # Сохраняем обновленные данные (с флагами для ручных проверок)
        save_data()
        
        logger.info(f"Восстановлено задач: {restored_count}")
        
        # Добавляем обработчик сигналов для корректного завершения
        def signal_handler(sig, frame):
            logger.info("Получен сигнал завершения, останавливаем бота...")
            application.stop_running()
            logger.info("Бот остановлен")
        
        import signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Запускаем бота
        logger.info("Запуск бота...")
        application.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)
        logger.info("Бот успешно запущен")
    
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        logger.exception(e)  # Полный стек ошибки

if __name__ == "__main__":
    main()  