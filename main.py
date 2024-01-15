import telebot
from telebot import types
import sqlite3
import schedule
import time
import threading

TOKEN = '6791339470:AAGpdDj7mJuWrTAlrGO4RZSZAxBmSzomhBw'
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы products и orders
cursor.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, image TEXT, sizes TEXT, colors TEXT, price INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    user_id INTEGER, 
    product_id INTEGER, 
    size TEXT, 
    color TEXT, 
    city TEXT, 
    district TEXT, 
    street TEXT, 
    house_num TEXT, 
    apartment_num TEXT, 
    postal_code TEXT,
    status_id INTEGER DEFAULT 0
)''')


# Проверяем существование столбца status_id и добавляем его, если он отсутствует
try:
    cursor.execute("SELECT status_id FROM orders LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute('''ALTER TABLE orders ADD COLUMN status_id INTEGER DEFAULT 1''')

# Создание таблицы statuses, если она еще не существует, и заполнение ее начальными данными
cursor.execute('''CREATE TABLE IF NOT EXISTS statuses (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT)''')
cursor.execute("SELECT COUNT(*) FROM statuses")
if cursor.fetchone()[0] == 0:
    statuses = [
        (0 , "Ваш заказ в обработке"),
        (1, "Ваш заказ принят"),
        (2, "Ваш заказ прибыл в Казахстан"),
        (3, "Ваш заказ отправлен доставкой в ваш город")
    ]
    cursor.executemany("INSERT INTO statuses (id, description) VALUES (?, ?)", statuses)
conn.commit()

user_data = {}


# Проверка наличия товаров в каталоге (в реальном приложении товары будут добавляться отдельно)
cursor.execute("SELECT COUNT(*) FROM products")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO products (name, description, image, sizes, colors, price) VALUES (?, ?, ?, ?, ?, ?)", 
                   ('Футболка', 'Качественная хлопковая футболка', 'image_url', 'S,M,L,XL', 'красный,синий,зеленый', 500))
    conn.commit()

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Добро пожаловать в наш магазин! Вот наш каталог:")
    show_catalog(message)

def show_catalog(message):
    cursor.execute("SELECT * FROM products WHERE IsHidden = TRUE")
    products = cursor.fetchall()
    for product in products:
        product_info = f"{product[1]}\nОписание: {product[2]}\nЦена: {product[6]} руб."
        markup = types.InlineKeyboardMarkup()
        order_button = types.InlineKeyboardButton("Заказать", callback_data=f"order_{product[0]}")
        markup.add(order_button)
        
        if product[3]:  # Если URL изображения существует
            bot.send_photo(message.chat.id, photo=product[3], caption=product_info, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, product_info, reply_markup=markup)

            bot.send_message(message.chat.id, product_info, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('order_'))
def order_product(call):
    product_id = call.data.split('_')[1]
    user_id = call.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['product_id'] = product_id

    cursor.execute("SELECT sizes, colors FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    sizes = product[0].split(',')
    colors = product[1].split(',')

    size_markup = types.InlineKeyboardMarkup()
    for size in sizes:
        size_button = types.InlineKeyboardButton(size, callback_data=f"size_{size}_{product_id}")
        size_markup.add(size_button)
    bot.send_message(call.message.chat.id, "Выберите размер:", reply_markup=size_markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('size_'))
def select_size(call):
    size, product_id = call.data.split('_')[1:]
    user_id = call.message.chat.id
    user_data[user_id]['size'] = size
      
    cursor.execute("SELECT colors FROM products WHERE id = ?", (product_id,))
    colors = cursor.fetchone()[0].split(',')
    color_markup = types.InlineKeyboardMarkup()
    for color in colors:
        color_button = types.InlineKeyboardButton(color, callback_data=f"color_{color}_{product_id}")
        color_markup.add(color_button)
    bot.send_message(call.message.chat.id, "Выберите цвет:", reply_markup=color_markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('color_'))
def select_color(call):
    color, product_id = call.data.split('_')[1:]
    user_id = call.message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['product_id'] = product_id
    user_data[user_id]['color'] = color
    bot.send_message(call.message.chat.id, f"Вы выбрали цвет: {color}. Теперь введите ваш город.")
    bot.register_next_step_handler(call.message, enter_city)

# Функции для ввода адреса
def enter_city(message):
    user_id = message.chat.id
    city = message.text
    user_data[user_id]['city'] = city
    # ...
    bot.send_message(message.chat.id, "Введите ваш район:")
    bot.register_next_step_handler(message, enter_district)

def enter_district(message):
    user_id = message.chat.id
    district = message.text
    user_data[user_id]['district'] = district
    # ...
    bot.send_message(message.chat.id, "Введите вашу улицу:")
    bot.register_next_step_handler(message, enter_street)

# Аналогично добавьте функции enter_street, enter_house_number и так далее

def enter_street(message):
    user_id = message.chat.id
    street = message.text
    user_data[user_id]['street'] = street
    bot.send_message(message.chat.id, "Введите номер дома:")
    bot.register_next_step_handler(message, enter_house_number)

def enter_house_number(message):
    user_id = message.chat.id
    house_number = message.text
    user_data[user_id]['house_num'] = house_number
    bot.send_message(message.chat.id, "Введите номер квартиры:")
    bot.register_next_step_handler(message, enter_apartment_number)

def enter_apartment_number(message):
    user_id = message.chat.id
    apartment_number = message.text
    user_data[user_id]['apartment_num'] = apartment_number
    bot.send_message(message.chat.id, "Введите почтовый индекс:")
    bot.register_next_step_handler(message, enter_postal_code)

def enter_postal_code(message):
    postal_code = message.text
    user_id = message.chat.id

    if user_id in user_data:
        user_data[user_id]['postal_code'] = postal_code
        # Здесь код для создания заказа в базе данных
        create_order(user_id, user_data[user_id])
        del user_data[user_id]  # Удаляем данные пользователя после создания заказа

    bot.send_message(message.chat.id, "Спасибо! Ваш заказ в обработке.")

def create_order(user_id, order_data):
    cursor.execute("INSERT INTO orders (user_id, product_id, size, color, city, district, street, house_num, apartment_num, postal_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                   (user_id, order_data['product_id'], order_data['size'], order_data['color'], order_data['city'], order_data['district'], order_data['street'], order_data['house_num'], order_data['apartment_num'], order_data['postal_code']))
    conn.commit()

def update_order_status(order_id, new_status_id):
    cursor.execute("UPDATE orders SET status_id = ? WHERE id = ?", (new_status_id, order_id))
    conn.commit()
    
STATUS_DESCRIPTIONS = {
    1: "Ваш заказ принят",
    2: "Ваш заказ прибыл в Казахстан",
    3: "Ваш заказ отправлен доставкой в ваш город"
}
def change_order_status(order_id, new_status_id):
    # Проверка на существование нового show_catalogа
    if new_status_id not in STATUS_DESCRIPTIONS:
        print("Неверный статус")
        return

    # Обновление статуса заказа и установка флага status_updated
    conn.commit()

    
def check_order_updates():
    print("Проверка обновлений заказов...")
    # Проверяем заказы, статус которых не равен 4
    cursor.execute("SELECT id, status_id, user_id FROM orders WHERE status_id != 4")
    orders = cursor.fetchall()
    print(f"Найдено заказов для обработки: {len(orders)}")

    for order_id, status_id, user_id in orders:
        if status_id in STATUS_DESCRIPTIONS:
            status_description = STATUS_DESCRIPTIONS[status_id]
            bot.send_message(user_id, f"Статус вашего заказа : {status_description}.")
            # Обновляем статус заказа на 4 после отправки уведомления
            cursor.execute("UPDATE orders SET status_id = 4 WHERE id = ?", (order_id,))
            conn.commit()



schedule.every(10).seconds.do(check_order_updates)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)
        
schedule.every(10).seconds.do(check_order_updates)

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.start()

bot.polling(none_stop=True)