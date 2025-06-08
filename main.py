import telebot
from telebot import types
from dotenv import load_dotenv
import threading
import time
from datetime import datetime
import os
import schedule 
from db_logic import DB_Manager

load_dotenv()

bot = telebot.TeleBot(os.getenv('TG_TOKEN'))
db_manager = DB_Manager(os.getenv('DATABASE'))


user_data = {}

def create_main_menu():
    """Создает главное меню с инлайн-кнопками"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("➕ Добавить напоминание", callback_data="add_reminder")
    btn2 = types.InlineKeyboardButton("📋 Мои напоминания", callback_data="my_reminders")
    btn3 = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    markup.add(btn1, btn2)
    markup.add(btn3)
    return markup

def create_reminder_list_markup(reminders, user_id):
    """Создает разметку для списка напоминаний"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for reminder in reminders:
        reminder_id, title, description, date, time, is_sent = reminder
        status = "✅" if is_sent else "⏰"
        btn_text = f"{status} {title} - {date} {time}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"view_reminder_{reminder_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    return markup

def create_reminder_actions_markup(reminder_id):
    """Создает разметку для действий с напоминанием"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_reminder_{reminder_id}")
    btn2 = types.InlineKeyboardButton("🔙 Назад", callback_data="my_reminders")
    markup.add(btn1, btn2)
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    """Обработчик команды /start"""
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для напоминаний. Помогу тебе не забыть важные дела!\n\n"
        "Выбери действие:",
        reply_markup=create_main_menu()
    )

@bot.message_handler(commands=['help'])
def help_message(message):
    """Обработчик команды /help"""
    help_text = """
🤖 **Как пользоваться ботом:**

➕ **Добавить напоминание** - создать новое напоминание
📋 **Мои напоминания** - посмотреть все напоминания
❓ **Помощь** - показать это сообщение

**Формат даты:** ДД.ММ.ГГГГ (например: 25.12.2024)
**Формат времени:** ЧЧ:ММ (например: 14:30)

Бот будет присылать напоминания точно в указанное время!
    """
    bot.send_message(message.chat.id, help_text, reply_markup=create_main_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Обработчик всех callback запросов"""
    user_id = call.from_user.id
    
    if call.data == "add_reminder":
        user_data[user_id] = {"step": "title"}
        bot.edit_message_text(
            "📝 Напишите название напоминания:",
            call.message.chat.id,
            call.message.message_id
        )


    elif call.data == "my_reminders":
        reminders = db_manager.get_user_reminders(user_id)
        if reminders:
            bot.edit_message_text(
                "📋 Ваши напоминания:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_reminder_list_markup(reminders, user_id)
            )
        else:
            bot.edit_message_text(
                "📭 У вас пока нет напоминаний.\n\nСоздайте первое напоминание!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_main_menu()
            )
    
    elif call.data == "help":
        help_text = """
🤖 **Как пользоваться ботом:**

➕ **Добавить напоминание** - создать новое напоминание
📋 **Мои напоминания** - посмотреть все напоминания
❓ **Помощь** - показать это сообщение

**Формат даты:** ДД.ММ.ГГГГ (например: 25.12.2024)
**Формат времени:** ЧЧ:ММ (например: 14:30)

Бот будет присылать напоминания точно в указанное время!
        """
        bot.edit_message_text(
            help_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_main_menu()
        )
    
    elif call.data == "back_to_menu":
        bot.edit_message_text(
            "🏠 Главное меню\n\nВыберите действие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_main_menu()
        )
    
    elif call.data.startswith("view_reminder_"):
        reminder_id = int(call.data.split("_")[2])
        reminder = db_manager.get_reminder_by_id(reminder_id, user_id)
        if reminder:
            reminder_id, title, description, date, time = reminder
            text = f"📌 **{title}**\n\n"
            if description:
                text += f"📄 Описание: {description}\n"
            text += f"📅 Дата: {date}\n⏰ Время: {time}"
            
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_reminder_actions_markup(reminder_id),
                parse_mode='Markdown'
            )
    
    elif call.data.startswith("delete_reminder_"):
        reminder_id = int(call.data.split("_")[2])
        db_manager.delete_reminder(reminder_id, user_id)
        bot.answer_callback_query(call.id, "🗑 Напоминание удалено!")
        
        reminders = db_manager.get_user_reminders(user_id)
        if reminders:
            bot.edit_message_text(
                "📋 Ваши напоминания:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_reminder_list_markup(reminders, user_id)
            )
        else:
            bot.edit_message_text(
                "📭 У вас больше нет напоминаний.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_main_menu()
            )

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    """Обработчик текстовых сообщений для создания напоминаний"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, используйте команду /start для начала работы.",
            reply_markup=create_main_menu()
        )
        return
    
    user_step = user_data[user_id].get("step")
    
    if user_step == "title":
        user_data[user_id]["title"] = message.text
        user_data[user_id]["step"] = "description"
        bot.send_message(
            message.chat.id,
            "📝 Теперь напишите описание напоминания (или отправьте '-' чтобы пропустить):"
        )
    
    elif user_step == "description":
        description = message.text if message.text != "-" else ""
        user_data[user_id]["description"] = description
        user_data[user_id]["step"] = "date"
        bot.send_message(
            message.chat.id,
            "📅 Введите дату напоминания в формате ДД.ММ.ГГГГ (например: 25.12.2024):"
        )
    
    elif user_step == "date":
        try:
            date_obj = datetime.strptime(message.text, "%d.%m.%Y")
            if date_obj.date() < datetime.now().date():
                bot.send_message(
                    message.chat.id,
                    "❌ Дата не может быть в прошлом. Введите корректную дату:"
                )
                return
            
            user_data[user_id]["date"] = message.text
            user_data[user_id]["step"] = "time"
            bot.send_message(
                message.chat.id,
                "⏰ Введите время напоминания в формате ЧЧ:ММ (например: 14:30):"
            )
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ:"
            )
    
    elif user_step == "time":
        try:
            time_obj = datetime.strptime(message.text, "%H:%M")
            
            reminder_date = datetime.strptime(user_data[user_id]["date"], "%d.%m.%Y").date()
            if reminder_date == datetime.now().date():
                reminder_time = time_obj.time()
                if reminder_time <= datetime.now().time():
                    bot.send_message(
                        message.chat.id,
                        "❌ Время не может быть в прошлом для сегодняшней даты. Введите корректное время:"
                    )
                    return
            
            db_manager.add_reminder(
                user_id,
                user_data[user_id]["title"],
                user_data[user_id]["description"],
                user_data[user_id]["date"],
                message.text
            )
            
            del user_data[user_id]
            
            bot.send_message(
                message.chat.id,
                f"✅ Напоминание создано!\n\n"
                f"📌 **{user_data.get(user_id, {}).get('title', 'Напоминание')}**\n"
                f"📅 {user_data.get(user_id, {}).get('date')}\n"
                f"⏰ {message.text}",
                reply_markup=create_main_menu(),
                parse_mode='Markdown'
            )
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Неверный формат времени. Используйте формат ЧЧ:ММ:"
            )

def check_reminders():
    """Проверяет и отправляет напоминания"""
    reminders = db_manager.get_pending_reminders()
    current_time = datetime.now()
    
    for reminder in reminders:
        reminder_id, user_id, title, description, date, time, *_ = reminder
        
        reminder_datetime = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")
        
        if reminder_datetime <= current_time:
            text = f"🔔 **НАПОМИНАНИЕ**\n\n📌 {title}"
            if description:
                text += f"\n📄 {description}"
            
            try:
                bot.send_message(user_id, text, parse_mode='Markdown')
                db_manager.mark_reminder_sent(reminder_id)
            except Exception as e:
                print(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

def reminder_scheduler():
    """Планировщик для проверки напоминаний"""
    schedule.every().minute.do(check_reminders)
    
    while True:
        schedule.run_pending()
        time.sleep(30) 

if __name__ == "__main__":
    db_manager.create_tables()
    
    scheduler_thread = threading.Thread(target=reminder_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("🤖 Бот запущен!")
    
    bot.infinity_polling()
