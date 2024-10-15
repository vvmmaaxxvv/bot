import os
import io
import re
import asyncio
from dotenv import load_dotenv
import asyncpg
import logging
import subprocess
import paramiko
from paramiko import AutoAddPolicy
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение переменных окружения
TOKEN = os.getenv("TOKEN")
RM_HOST = os.getenv("RM_HOST")
RM_PORT = int(os.getenv("RM_PORT", 22))
RM_USER = os.getenv("RM_USER")
RM_PASSWORD = os.getenv("RM_PASSWORD")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_DATABASE = os.getenv("DB_DATABASE")

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log',
    filemode='a'  # Можно установить 'w' для перезаписи лога при каждом запуске
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
GET_EMAILS_TEXT, CONFIRM_EMAIL, GET_PHONES_TEXT, CONFIRM_PHONE, VERIFY_PASSWORD, APT_LIST_CHOICE, APT_PACKAGE_NAME = range(7)

# Регулярные выражения
PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$'
EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_REGEX = re.compile(
        r"(?:\+7|8)[\s\-]?"
        r"(?:\(?\d{3}\)?|\d{3})"
        r"[\s\-]?\d{3}"
        r"[\s\-]?\d{2}"
        r"[\s\-]?\d{2}"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение при вводе команды /start."""
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Привет {user.mention_markdown_v2()}\! Я готов помочь\. Вот доступные команды:\n'
        '/start - Запуск Бота\n'
        '/cancel - Отмена\n'
        '/find_phone_numbers - Поиск телефонных номеров в тексте\n'
        '/find_email_address - Поиск Email адресов в тексте\n'
        '/verify_password - Проверка сложности пароля\n'
        '/get_release - Информация о релизе\n'
        '/get_uname - Информация об архитектуре процессора, имени хоста системы и версии ядра\n'
        '/get_uptime - Информация о времени работы\n'
        '/get_df - Информация о состоянии файловой системы\n'
        '/get_free - Информация о состоянии оперативной памяти\n'
        '/get_mpstat - Информация о производительности системы\n'
        '/get_w - Информация о работающих в данной системе пользователях\n'
        '/get_auths - Информация о последних 10 входах в систему\n'
        '/get_critical - Информация о последних 5 критических событиях\n'
        '/get_ps - Информация о запущенных процессах\n'
        '/get_ss - Информация об используемых портах\n'
        '/get_apt_list - Информация об установленных пакетах\n'
        '/get_services - Информация о запущенных сервисах\n'
        '/get_repl_logs - Вывод логов о репликации\n'
        '/get_emails - Вывод Email адресов адресов почты из таблицы\n'
        '/get_phone_numbers - Вывод телефонных номеров из таблицы'
    )
    logger.info(f"User {user.id} started the bot.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cancel для отмены текущей операции."""
    await update.message.reply_text('Операция отменена.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Функция для выполнения SSH-команд
def execute_ssh_command(command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()
        client.close()
        if error:
            return f"Ошибка при выполнении команды: {error}"
        else:
            return output
    except Exception as e:
        return f"Не удалось выполнить команду по SSH: {e}"

# Информация о релизе системы
async def get_release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_release")
    response = execute_ssh_command('cat /etc/os-release')
    await update.message.reply_text(response)

# Информация об архитектуре процессора, имени хоста и версии ядра
async def get_uname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_uname")
    response = execute_ssh_command('uname -a')
    await update.message.reply_text(response)

# Информация о времени работы системы
async def get_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_uptime")
    response = execute_ssh_command('uptime -p')
    await update.message.reply_text(response)

# Состояние файловой системы
async def get_df(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_df")
    response = execute_ssh_command('df -h')
    await update.message.reply_text(response)

# Состояние оперативной памяти
async def get_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_free")
    response = execute_ssh_command('free -h')
    await update.message.reply_text(response)

# Производительность системы
async def get_mpstat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_mpstat")
    response = execute_ssh_command('mpstat -P ALL 1 1')
    await update.message.reply_text(response)

# Информация о пользователях в системе
async def get_w(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_w")
    response = execute_ssh_command('w')
    await update.message.reply_text(response)

# Последние 10 входов в систему
async def get_auths(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_auths")
    response = execute_ssh_command('last -n 10')
    await update.message.reply_text(response)

# Последние 5 критических событий
async def get_critical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_critical")
    response = execute_ssh_command('journalctl -p crit -n 5')
    await update.message.reply_text(response)

# Список запущенных процессов
async def get_ps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_ps")
    response = execute_ssh_command('ps aux --sort=-%mem | head -n 10')
    await update.message.reply_text(response)

# Используемые порты
async def get_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_ss")
    response = execute_ssh_command('ss -tuln')
    await update.message.reply_text(response)

# Сбор информации о запущенных сервисах
async def get_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_services")
    response = execute_ssh_command('systemctl list-units --type=service --state=running')
    await update.message.reply_text(response)

async def verify_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает пароль для проверки сложности."""
    await update.message.reply_text('Пожалуйста, отправьте пароль для проверки его сложности.')
    return VERIFY_PASSWORD


async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверяет сложность пароля."""
    password = update.message.text
    if re.match(PASSWORD_REGEX, password):
        response = "Пароль сложный"
    else:
        response = "Пароль простой"
    await update.message.reply_text(response)
    logger.info("Processed /verify_password command.")
    return ConversationHandler.END

# Начало разговора с пользователем
async def get_apt_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested /get_apt_list")
    await update.message.reply_text(
        "Выберите опцию:\n"
        "1. Вывести список всех установленных пакетов\n"
        "2. Поиск информации о пакете\n"
        "Введите *1* или *2*. Для отмены введите /cancel.",
        parse_mode='Markdown'
    )
    return APT_LIST_CHOICE

# Обработка выбора пользователя
async def apt_list_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    if choice == '1':
        logger.info(f"User {update.effective_user.id} chose to list all packages")
        response = execute_ssh_command('dpkg -l')

        # Проверяем длину ответа
        if len(response) < 4096:
            await update.message.reply_text(response)
        else:
            # Отправляем как файл, если сообщение слишком длинное
            with open('apt_list.txt', 'w') as f:
                f.write(response)
            await update.message.reply_document(document=open('apt_list.txt', 'rb'))
            os.remove('apt_list.txt')  # Удаляем файл после отправки
        return ConversationHandler.END
    elif choice == '2':
        await update.message.reply_text("Введите название пакета для поиска:")
        return APT_PACKAGE_NAME
    else:
        await update.message.reply_text("Пожалуйста, введите *1* или *2*. Для отмены введите /cancel.",
                                        parse_mode='Markdown')
        return APT_LIST_CHOICE

# Обработка поиска пакета
async def apt_package_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    package_name = update.message.text.strip()
    logger.info(f"User {update.effective_user.id} searched for package {package_name}")
    response = execute_ssh_command(f'dpkg -l | grep -i {package_name}')
    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(f"Пакет *{package_name}* не найден среди установленных.", parse_mode='Markdown')
    return ConversationHandler.END

async def get_repl_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /get_repl_logs для получения файла логов."""
    logger.info("Пользователь запросил репликационные логи.")
    try:
        logger.info(f"Выполнение команды: /get_repl_logs")

        log_data = subprocess.run(
            ["bash", "-c", f"cat /var/log/postgresql/postgresql.csv | grep repl | tail -n 15"],
            capture_output=True,
            text=True
        ).stdout
        if log_data:
            await update.message.reply_text(f"Последние репликационные логи:\n{log_data}")
        else:
            await update.message.reply_text("Файл логов пуст.")
    except paramiko.SSHException as pe:
        logger.error(f"Ошибка SSH-соединения: {pe}")
        await update.message.reply_text("Не удалось установить SSH-соединение. Проверьте настройки подключения.")
    except Exception as e:
        logger.exception("Ошибка при получении репликационных логов.")
        await update.message.reply_text(f"Ошибка при получении репликационных логов: {e}")

async def start_get_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса поиска Email-адресов."""
    await update.message.reply_text(
        "Пожалуйста, отправьте текст для поиска email-адресов.",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_EMAILS_TEXT

async def receive_emails_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение текста и поиск Email-адресов."""
    text = update.message.text
    emails = list(set(EMAIL_REGEX.findall(text)))
    if not emails:
        await update.message.reply_text("В предоставленном тексте не найдено email-адресов.")
        return ConversationHandler.END
    message = (
        "Найдены следующие email-адреса:\n"
        + "\n".join(emails)
        + "\n\nХотите сохранить их в базу данных? (да/нет)"
    )
    context.user_data['emails'] = emails
    await update.message.reply_text(message)
    return CONFIRM_EMAIL

async def confirm_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение сохранения найденных Email-адресов в базе данных."""
    response = update.message.text.lower()
    if response in ['да', 'д', 'yes', 'y']:
        emails = context.user_data.get('emails', [])
        try:
            conn = await asyncpg.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_DATABASE,
                host=DB_HOST,
                port=DB_PORT,
            )
            await conn.executemany(
                'INSERT INTO emails(email) VALUES($1) ON CONFLICT DO NOTHING',
                [(email,) for email in emails]
            )
            await conn.close()
            await update.message.reply_text("Email-адреса успешно сохранены в базу данных.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при сохранении в базу данных: {e}")
    else:
        await update.message.reply_text("Операция отменена. Email-адреса не были сохранены.")
    return ConversationHandler.END

async def start_get_phones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса поиска номеров телефонов."""
    await update.message.reply_text(
        "Пожалуйста, отправьте текст для поиска номеров телефонов.",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_PHONES_TEXT

async def receive_phones_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение текста и поиск номеров телефонов."""
    text = update.message.text
    phones = list(set(PHONE_REGEX.findall(text)))
    if not phones:
        await update.message.reply_text("В предоставленном тексте не найдено номеров телефонов.")
        return ConversationHandler.END
    message = (
        "Найдены следующие номера телефонов:\n"
        + "\n".join(phones)
        + "\n\nХотите сохранить их в базу данных? (да/нет)"
    )
    context.user_data['phones'] = phones
    await update.message.reply_text(message)
    return CONFIRM_PHONE

async def confirm_phones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение сохранения найденных номеров телефонов в базе данных."""
    response = update.message.text.lower()
    if response in ['да', 'д', 'yes', 'y']:
        phones = context.user_data.get('phones', [])
        try:
            conn = await asyncpg.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_DATABASE,
                host=DB_HOST,
                port=DB_PORT,
            )
            await conn.executemany(
                'INSERT INTO phones(phone_number) VALUES($1) ON CONFLICT DO NOTHING',
                [(phone,) for phone in phones]
            )
            await conn.close()
            await update.message.reply_text("Номера телефонов успешно сохранены в базу данных.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при сохранении в базу данных: {e}")
    else:
        await update.message.reply_text("Операция отменена. Номера телефонов не были сохранены.")
    return ConversationHandler.END

async def find_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find_email."""
    return await start_get_emails(update, context)

async def find_phone_numbers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find_phone_number."""
    return await start_get_phones(update, context)

async def get_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /get_emails для вывода данных из таблицы emails."""
    logger.info("Пользователь запросил список email-адресов.")
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE
        )
        records = await conn.fetch("SELECT email FROM emails;")
        await conn.close()

        if records:
            emails = [record['email'] for record in records]
            formatted_emails = "\n".join(emails)
            if len(formatted_emails) > 4000:
                # Telegram ограничение на длину сообщения
                await update.message.reply_text("Слишком много email-адресов для отправки в одном сообщении.")
            else:
                await update.message.reply_text(f"Список email-адресов:\n{formatted_emails}")
        else:
            await update.message.reply_text("Таблица email-адресов пуста.")
    except Exception as e:
        logger.exception("Ошибка при получении email-адресов из базы данных.")
        await update.message.reply_text(f"Ошибка при получении email-адресов: {e}")

async def get_phone_numbers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /get_phone_numbers для вывода данных из таблицы phones."""
    logger.info("Пользователь запросил список номеров телефонов.")
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE
        )
        records = await conn.fetch("SELECT phone_number FROM phones;")
        await conn.close()

        if records:
            phone_numbers = [record['phone_number'] for record in records]
            formatted_phones = "\n".join(phone_numbers)
            if len(formatted_phones) > 4000:
                # Telegram ограничение на длину сообщения
                await update.message.reply_text("Слишком много номеров телефонов для отправки в одном сообщении.")
            else:
                await update.message.reply_text(f"Список номеров телефонов:\n{formatted_phones}")
        else:
            await update.message.reply_text("Таблица номеров телефонов пуста.")
    except Exception as e:
        logger.exception("Ошибка при получении номеров телефонов из базы данных.")
        await update.message.reply_text(f"Ошибка при получении номеров телефонов: {e}")

def main():
    """Главная функция для запуска бота."""
    application = ApplicationBuilder().token(TOKEN).build()

    # Добавление обработчика команды /start
    application.add_handler(CommandHandler("start", start))
    logger.debug("Обработчик /start добавлен.")

    # Обработчик команды /get_repl_logs
    application.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    logger.debug("Обработчик /get_repl_logs добавлен.")

    # Обработчик команды /get_emails
    get_emails_handler = CommandHandler('get_emails', get_emails_command)
    application.add_handler(get_emails_handler)
    logger.debug("Обработчик /get_emails добавлен.")

    # Обработчик команды /get_phone_numbers
    get_phone_numbers_handler = CommandHandler('get_phone_numbers', get_phone_numbers_command)
    application.add_handler(get_phone_numbers_handler)
    logger.debug("Обработчик /get_phone_numbers добавлен.")

    # Добавление обработчика команды /get_release
    application.add_handler(CommandHandler("get_release", get_release))
    logger.debug("Обработчик /get_release добавлен.")

    # Добавление обработчика команды /get_uname
    application.add_handler(CommandHandler("get_uname", get_uname))
    logger.debug("Обработчик /get_uname добавлен.")

    # Добавление обработчика команды /get_uptime
    application.add_handler(CommandHandler("get_uptime", get_uptime))
    logger.debug("Обработчик /get_uptime добавлен.")

    # Добавление обработчика команды /get_df
    application.add_handler(CommandHandler("get_df", get_df))
    logger.debug("Обработчик /get_df добавлен.")

    # Добавление обработчика команды /get_free
    application.add_handler(CommandHandler("get_free", get_free))
    logger.debug("Обработчик /get_free добавлен.")

    # Добавление обработчика команды /get_mpstat
    application.add_handler(CommandHandler("get_mpstat", get_mpstat))
    logger.debug("Обработчик /get_mpstat добавлен.")

    # Добавление обработчика команды /get_w
    application.add_handler(CommandHandler("get_w", get_w))
    logger.debug("Обработчик /get_w добавлен.")

    # Добавление обработчика команды /get_auths
    application.add_handler(CommandHandler("get_auths", get_auths))
    logger.debug("Обработчик /get_auths добавлен.")

    # Добавление обработчика команды /get_critical
    application.add_handler(CommandHandler("get_critical", get_critical))
    logger.debug("Обработчик /get_critical добавлен.")

    # Добавление обработчика команды /get_services
    application.add_handler(CommandHandler("get_services", get_services))
    logger.debug("Обработчик /get_services добавлен.")

    # Добавление обработчика команды /get_ps
    application.add_handler(CommandHandler("get_ps", get_ps))
    logger.debug("Обработчик /get_ps добавлен.")

    # Добавление обработчика команды /get_ss
    application.add_handler(CommandHandler("get_ss", get_ss))
    logger.debug("Обработчик /get_ss добавлен.")

    # Обработчик команды /find_email с использованием ConversationHandler
    emails_conv = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_emails_command)],
        states={
            GET_EMAILS_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emails_text)],
            CONFIRM_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_emails)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(emails_conv)

    # Обработчик команды /find_phone_number с использованием ConversationHandler
    phones_conv = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_numbers_command)],
        states={
            GET_PHONES_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phones_text)],
            CONFIRM_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_phones)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(phones_conv)

    # Конфигурирование ConversationHandler для проверки пароля
    password_conv = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_start)],
        states={
            VERIFY_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(password_conv)
    # Конфигурирование ConversationHandler для /get_apt_list
    apt_list_handler = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list)],
        states={
            APT_LIST_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_list_choice)],
            APT_PACKAGE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_package_search)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(apt_list_handler)

    # Запуск бота (начало polling, бот будет слушать новые сообщения)
    logger.info("Бот запущен и начинает polling.")
    application.run_polling()

if __name__ == '__main__':
    main()