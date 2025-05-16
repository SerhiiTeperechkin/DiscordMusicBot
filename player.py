"""
Модуль музыкального плеера для Discord бота.
Реализует класс MusicPlayer для управления очередью и воспроизведением треков.
"""

import asyncio
from async_timeout import timeout
from config import PLAYER_TIMEOUT, DEFAULT_VOLUME

class MusicPlayer:
    """Класс для управления музыкой и очередью треков."""
    
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 
                 'current', 'np', 'volume', 'loop')
    
    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog
        
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        
        self.np = None  # Текущий трек (сообщение)
        self.volume = DEFAULT_VOLUME
        self.current = None  # Текущий трек (источник)
        self.loop = False  # Флаг повтора трека
        
        ctx.bot.loop.create_task(self.player_loop())
    
    async def player_loop(self):
        """Главный цикл проигрывателя."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            self.next.clear()
            
            try:
                # Ждем следующий трек с таймаутом
                async with timeout(PLAYER_TIMEOUT):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                # Выходим из голосового канала после таймаута
                return self.destroy(self._guild)
            
            # Сохраняем текущий трек
            self.current = source
            
            # Воспроизводим трек
            try:
                self._guild.voice_client.play(
                    source, 
                    after=lambda error: self.bot.loop.call_soon_threadsafe(
                        self.next.set
                    )
                )
                
                # Отображаем информацию о треке
                self.np = await self._channel.send(
                    f'🎵 Сейчас играет: **{source.title}**{source.duration_string}'
                )
                
                # Ждем завершения трека
                await self.next.wait()
                
                # Если включен повтор трека, добавляем его снова в очередь
                if self.loop and self.current:
                    await self.queue.put(self.current)
            
            except Exception as e:
                await self._channel.send(f"❌ Ошибка воспроизведения: {str(e)}")
                continue
            
            finally:
                # Очищаем ресурсы
                if hasattr(source, 'cleanup'):
                    source.cleanup()
                self.current = None
        
        return None

    def destroy(self, guild):
        """Уничтожает плеер и отключается от голосового канала."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))
