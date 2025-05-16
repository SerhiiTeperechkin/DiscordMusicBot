"""
Модуль для работы с аудио-источниками через yt-dlp.
Обрабатывает загрузку и потоковую передачу аудио из различных источников.
"""

import asyncio
import ssl
import discord
import yt_dlp
from config import YTDL_FORMAT_OPTIONS, FFMPEG_OPTIONS

class YTDLSource(discord.PCMVolumeTransformer):
    """Класс для работы с аудио-источниками через yt-dlp."""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title', 'Неизвестный трек')
        self.url = data.get('webpage_url', data.get('url', ''))
        self.duration = data.get('duration', 0)
        
    @property
    def duration_string(self):
        """Возвращает длительность трека в формате MM:SS."""
        if not self.duration:
            return ""
        
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f" [{minutes}:{seconds:02d}]"

    @classmethod
    async def create_ytdl_instance(cls):
        """Создает экземпляр YoutubeDL с актуальными настройками."""
        ytdl_opts = YTDL_FORMAT_OPTIONS.copy()
        # Дополнительные настройки для обхода SSL проблем
        ytdl_opts.update({
            'nocheckcertificate': True,
            'no_check_certificate': True,
            'no_check_certificates': True,
            'prefer_insecure': True,
            'verify_ssl': False,
        })
        return yt_dlp.YoutubeDL(ytdl_opts)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True, ffmpeg_path="ffmpeg"):
        """Получает аудио из URL с обработкой ошибок и повторными попытками."""
        loop = loop or asyncio.get_event_loop()
        
        # Максимальное количество попыток
        max_retries = 5
        retries = 0
        
        # Сохраняем оригинальный SSL контекст
        original_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        
        try:
            while retries < max_retries:
                try:
                    # Создаем экземпляр yt-dlp
                    ytdl = await cls.create_ytdl_instance()
                    
                    # Преобразуем поисковый запрос в формат ytsearch, если это не URL
                    if not url.startswith(('http://', 'https://')):
                        url = f"ytsearch1:{url}"
                    
                    # Извлекаем информацию о видео
                    data = await loop.run_in_executor(
                        None, 
                        lambda: ytdl.extract_info(url, download=not stream)
                    )
                    
                    # Обрабатываем плейлисты
                    if data and 'entries' in data:
                        data = data['entries'][0]
                    
                    if not data:
                        raise ValueError("Не удалось извлечь данные аудио")
                    
                    # Получаем URL для потока или локальный путь
                    processed_url = data.get('url') if stream else ytdl.prepare_filename(data)
                    if not processed_url:
                        raise ValueError("Не удалось получить URL потока")
                    
                    # Создаем аудио-источник
                    audio_source = discord.FFmpegPCMAudio(
                        processed_url,
                        executable=ffmpeg_path,
                        **FFMPEG_OPTIONS
                    )
                    
                    return cls(audio_source, data=data)
                
                except ssl.SSLError as e:
                    retries += 1
                    print(f"SSL ошибка (попытка {retries}/{max_retries}): {e}")
                    
                    # Пауза перед повторной попыткой
                    if retries < max_retries:
                        await asyncio.sleep(2)
                    else:
                        raise ValueError(f"Не удалось подключиться из-за проблем с SSL: {e}")
                
                except Exception as e:
                    print(f"Ошибка при извлечении аудио: {e}")
                    raise ValueError(f"Не удалось извлечь аудио: {e}")
        
        finally:
            # Восстанавливаем оригинальный SSL контекст
            ssl._create_default_https_context = original_context
