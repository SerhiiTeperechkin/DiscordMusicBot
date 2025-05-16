"""
Конфигурационный модуль для музыкального Discord бота.
Содержит основные настройки и конфигурации для подсистем.
"""

import os
import ssl
import shutil
import platform
import certifi

# Настройка команд
COMMAND_PREFIX = '!'
BOT_DESCRIPTION = 'Музыкальный бот для Discord'

# Настройка FFmpeg
def find_ffmpeg():
    """Находит путь к исполняемому файлу FFmpeg."""
    ffmpeg_path_in_system = shutil.which("ffmpeg")
    if ffmpeg_path_in_system:
        print(f"✅ FFmpeg найден в PATH: {ffmpeg_path_in_system}")
        return ffmpeg_path_in_system
    
    # Проверка стандартных путей установки
    fallback_paths = [
        "C:\\ffmpeg\\bin\\ffmpeg.exe",  # Windows
        "/usr/bin/ffmpeg",              # Linux
        "/usr/local/bin/ffmpeg"         # macOS
    ]
    
    for path in fallback_paths:
        if os.path.exists(path):
            print(f"✅ FFmpeg найден по пути: {path}")
            return path
    
    print("❌ ВНИМАНИЕ: FFmpeg не найден!")
    print("Пожалуйста, установите FFmpeg согласно инструкции в README.md")
    return "ffmpeg"  # Возвращаем базовое имя как последнюю надежду

# Настройка SSL
def configure_ssl():
    """Настраивает SSL сертификаты и контекст для безопасных соединений."""
    # Выводим информацию о системе для отладки
    print(f"Python версия: {platform.python_version()}")
    print(f"Операционная система: {platform.system()} {platform.release()}")
    print(f"SSL версия: {ssl.OPENSSL_VERSION}")
    print(f"Путь к сертификатам: {certifi.where()}")
    
    # Создаем безопасный SSL контекст с сертификатами certifi
    ssl_context = ssl.create_default_context()
    ssl_context.load_verify_locations(certifi.where())
    
    # Для устранения проблем с некоторыми соединениями
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Устанавливаем контекст по умолчанию для всех HTTPS соединений
    ssl._create_default_https_context = ssl._create_unverified_context
    
    return ssl_context

# Настройки yt-dlp
YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,  # Разрешаем плейлисты
    'nocheckcertificate': True,
    'ignoreerrors': False,  # Изменено для обнаружения ошибок в плейлистах
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'cachedir': False,
    'extract_flat': False,  # Изменено для получения полных данных плейлиста
    'socket_timeout': 15,
    'retries': 15,
    'fragment_retries': 15,
    'skip_download': False,
}

# Настройки для получения данных о плейлисте
YTDL_PLAYLIST_OPTIONS = YTDL_FORMAT_OPTIONS.copy()
YTDL_PLAYLIST_OPTIONS.update({
    'extract_flat': 'in_playlist',  # Режим для определения плейлиста
    'dump_single_json': True,
    'noplaylist': False,  # Важно: разрешаем обработку плейлистов
    'playlistend': 100,    # Ограничиваем количество треков для анализа
    'ignore_no_formats_error': True,
})

# Настройки FFmpeg
FFMPEG_OPTIONS = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

# Настройки плеера
PLAYER_TIMEOUT = 180  # Тайм-аут в секундах перед автоматическим отключением
DEFAULT_VOLUME = 0.5  # Громкость по умолчанию (0.0 - 1.0)
