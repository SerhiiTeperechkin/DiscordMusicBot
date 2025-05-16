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
    async def is_playlist(cls, url, loop=None):
        """Проверяет, является ли URL плейлистом."""
        if not url.startswith(('http://', 'https://')):
            return False
            
        # Проверка на явный признак плейлиста в URL (параметр list)
        if '&list=' in url or '?list=' in url:
            print(f"Обнаружен параметр плейлиста в URL: {url}")
            return True
            
        loop = loop or asyncio.get_event_loop()
        
        # Создаем экземпляр yt-dlp с опциями для плейлиста
        from config import YTDL_PLAYLIST_OPTIONS
        ytdl_opts = YTDL_PLAYLIST_OPTIONS.copy()
        ytdl_opts.update({
            'dump_single_json': True,
            'quiet': False,  # Включаем вывод для отладки
            'extract_flat': 'in_playlist',
        })
        ytdl = yt_dlp.YoutubeDL(ytdl_opts)
        
        try:
            # Извлекаем информацию о плейлисте с полной обработкой
            print(f"Проверка плейлиста для: {url}")
            info = await loop.run_in_executor(
                None, 
                lambda: ytdl.extract_info(url, download=False, process=True)
            )
            
            # Выводим диагностическую информацию
            has_entries = 'entries' in info
            entries_count = len(info.get('entries', [])) if has_entries else 0
            print(f"Результат проверки плейлиста: есть 'entries': {has_entries}, количество: {entries_count}")
            
            # Проверяем, является ли это плейлистом
            is_playlist_result = has_entries and entries_count > 0
            print(f"URL распознан как плейлист: {is_playlist_result}")
            return is_playlist_result
            
        except Exception as e:
            print(f"Ошибка при проверке плейлиста: {e}")
            
            # Дополнительная проверка на параметр плейлиста в URL
            if '&list=' in url or '?list=' in url:
                print("URL содержит параметр list, считаем его плейлистом несмотря на ошибку")
                return True
                
            return False
    
    @classmethod
    async def get_playlist_items(cls, url, *, loop=None, ffmpeg_path="ffmpeg"):
        """Извлекает все треки из плейлиста."""
        loop = loop or asyncio.get_event_loop()
        
        # Подготавливаем специальные настройки для извлечения плейлиста
        from config import YTDL_PLAYLIST_OPTIONS
        ytdl_opts = YTDL_PLAYLIST_OPTIONS.copy()
        ytdl_opts.update({
            'noplaylist': False,  # Разрешаем обработку плейлистов
            'extract_flat': False,  # Получаем полные данные
            'ignoreerrors': True,   # Продолжаем при ошибках отдельных видео
        })
        
        # Создаем экземпляр yt-dlp
        ytdl = yt_dlp.YoutubeDL(ytdl_opts)
        
        # Сохраняем оригинальный SSL контекст
        original_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        
        try:
            print(f"Получение данных плейлиста для: {url}")
            # Извлекаем информацию о плейлисте с полной обработкой
            data = await loop.run_in_executor(
                None, 
                lambda: ytdl.extract_info(url, download=False, process=True)
            )
            
            if not data:
                raise ValueError("Не удалось извлечь данные плейлиста")
            
            playlist_title = data.get('title', 'Плейлист')
            print(f"Название плейлиста: {playlist_title}")
            
            # Получаем все треки из плейлиста
            tracks = []
            
            # Проверяем наличие треков
            if 'entries' in data:
                entries = data['entries']
                print(f"Найдено {len(entries)} треков в плейлисте")
                
                # Создаем объекты YTDLSource для каждого трека
                for i, entry in enumerate(entries):
                    if entry is None:
                        print(f"Пропуск пустой записи #{i+1}")
                        continue
                    
                    try:
                        # Если это прямой URL, используем его
                        if 'url' in entry:
                            processed_url = entry['url']
                        # Иначе нам нужно получить данные для потока
                        elif 'id' in entry and 'webpage_url' in entry:
                            entry_data = await loop.run_in_executor(
                                None,
                                lambda: ytdl.extract_info(entry['webpage_url'], download=False)
                            )
                            processed_url = entry_data.get('url')
                        else:
                            print(f"Пропуск трека #{i+1}: не найден URL")
                            continue
                            
                        if not processed_url:
                            print(f"Пропуск трека #{i+1}: не получен URL потока")
                            continue
                        
                        # Создаем аудио-источник
                        audio_source = discord.FFmpegPCMAudio(
                            processed_url,
                            executable=ffmpeg_path,
                            **FFMPEG_OPTIONS
                        )
                        
                        track = cls(audio_source, data=entry)
                        tracks.append(track)
                        print(f"Добавлен трек #{i+1}: {track.title}")
                    
                    except Exception as track_error:
                        print(f"Ошибка при обработке трека #{i+1}: {track_error}")
                        continue
                
            return playlist_title, tracks
        
        except Exception as e:
            print(f"Критическая ошибка при извлечении плейлиста: {e}")
            raise ValueError(f"Не удалось извлечь плейлист: {e}")
        
        finally:
            # Восстанавливаем оригинальный SSL контекст
            ssl._create_default_https_context = original_context
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True, ffmpeg_path="ffmpeg", process_playlist=False):
        """Получает аудио из URL с обработкой ошибок и повторными попытками."""
        loop = loop or asyncio.get_event_loop()
        
        # Максимальное количество попыток
        max_retries = 5
        retries = 0
        
        # Сохраняем оригинальный SSL контекст
        original_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        
        try:
            # Проверяем, является ли это плейлистом и нужно ли его обрабатывать
            if process_playlist and await cls.is_playlist(url, loop=loop):
                # Возвращаем специальный маркер, указывающий что это плейлист
                return {'is_playlist': True, 'url': url}
            
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
                    
                    # Обрабатываем плейлисты, если не нужно обрабатывать весь плейлист,
                    # берем только первый трек
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
