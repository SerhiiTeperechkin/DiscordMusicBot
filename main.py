"""
Музыкальный Discord бот для воспроизведения музыки из YouTube.
Главный файл программы с точкой входа.
"""

import os
import discord
from discord.ext import commands
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import requests
from dotenv import load_dotenv

# Импортируем модули проекта
from config import COMMAND_PREFIX, BOT_DESCRIPTION, configure_ssl
from music_commands import Music

# Отключаем предупреждения SSL для requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Настраиваем SSL для безопасных соединений
ssl_context = configure_ssl()

# Настройка и создание бота
def create_bot():
    """Создает и настраивает экземпляр бота Discord."""
    
    # Настройка привилегий бота
    intents = discord.Intents.default()
    intents.message_content = True
    
    # Создание экземпляра бота с нужными настройками
    bot = commands.Bot(
        command_prefix=COMMAND_PREFIX, 
        description=BOT_DESCRIPTION,
        intents=intents
    )
    
    # Добавляем обработчик события готовности
    @bot.event
    async def on_ready():
        """Вызывается, когда бот полностью готов к работе."""
        print("="*50)
        print(f"✅ Бот {bot.user.name} успешно запущен!")
        print(f"ID: {bot.user.id}")
        print(f"Префикс команд: {COMMAND_PREFIX}")
        print("="*50)
    
    # Возвращаем настроенный экземпляр бота
    return bot

# Настройка и запуск бота
async def setup_hook(bot):
    """Настраивает модули бота."""
    # Добавляем музыкальные команды
    await bot.add_cog(Music(bot))
    print("✅ Музыкальный модуль успешно загружен")

# Получение токена из файла .env или запрос у пользователя
def get_token():
    """Получает токен Discord из .env файла или запрашивает у пользователя."""
    # Пытаемся загрузить токен из .env файла
    try:
        load_dotenv()
        token = os.getenv("DISCORD_TOKEN")
        if token:
            print("✅ Токен успешно загружен из .env файла")
            return token
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке .env файла: {e}")
    
    # Если токен не найден, запрашиваем у пользователя
    print("\n❗ Токен Discord не найден в .env файле")
    token = input("➡️ Введите токен вашего Discord бота: ")
    
    # Предлагаем сохранить токен в .env файл
    save = input("Сохранить токен в .env файл для будущего использования? (y/n): ")
    if save.lower() == 'y':
        try:
            with open('.env', 'w') as f:
                f.write(f"DISCORD_TOKEN={token}")
            print("✅ Токен сохранен в .env файл")
        except Exception as e:
            print(f"❌ Не удалось сохранить токен: {e}")
    
    return token

# Главная функция программы
def main():
    """Основная функция для запуска бота."""
    # Создаем и настраиваем бота
    bot = create_bot()
    
    # Устанавливаем хук для настройки модулей
    bot.setup_hook = lambda: setup_hook(bot)
    
    # Получаем токен
    token = get_token()
    
    # Запускаем бота
    print("🚀 Запуск бота...")
    bot.run(token)

# Точка входа в программу
if __name__ == "__main__":
    main()
