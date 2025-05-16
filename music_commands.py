"""
Модуль с командами для управления музыкой.
Реализует класс Music для обработки музыкальных команд Discord бота.
"""

import discord
from discord.ext import commands
from player import MusicPlayer
from ytdl_source import YTDLSource
from config import find_ffmpeg

class Music(commands.Cog):
    """Команды для управления музыкой."""
    
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.ffmpeg_path = find_ffmpeg()
    
    async def cleanup(self, guild):
        """Очищает ресурсы и отключается от голосового канала."""
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass
        
        try:
            del self.players[guild.id]
        except KeyError:
            pass
    
    def get_player(self, ctx):
        """Получает или создает плеер для гильдии."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        
        return player
    
    @commands.command(name='join', help='Присоединяется к голосовому каналу')
    async def join(self, ctx):
        """Присоединяется к голосовому каналу пользователя."""
        if ctx.author.voice is None:
            return await ctx.send("Вы не подключены к голосовому каналу.")
    
        destination = ctx.author.voice.channel
    
        if ctx.voice_client:
            await ctx.voice_client.move_to(destination)
        else:
            await destination.connect()
    
        await ctx.send(f"✅ Подключен к каналу: {destination.name}")

    @commands.command(name='play', help='Воспроизводит музыку из YouTube')
    async def play(self, ctx, *, url):
        """Воспроизводит или добавляет трек в очередь."""
        # Проверяем, подключен ли бот к голосовому каналу
        if not ctx.voice_client:
            await ctx.invoke(self.join)
        
        # Получаем плеер для этой гильдии
        player = self.get_player(ctx)
        
        # Отправляем промежуточное сообщение
        searching_message = await ctx.send("🔄 Обрабатываю запрос...")
        
        # Обрабатываем поисковый запрос или URL
        async with ctx.typing():
            try:
                # Проверяем, является ли URL плейлистом
                is_playlist = False
                if url.startswith(('http://', 'https://')):
                    is_playlist = await YTDLSource.is_playlist(url, loop=self.bot.loop)
                
                if is_playlist:
                    await searching_message.edit(
                        content=f'ℹ️ Обнаружен плейлист YouTube. Добавляю только первый трек. Используйте `!playlist {url}` для добавления всего плейлиста.'
                    )
                
                # Получаем аудио-источник
                source = await YTDLSource.from_url(
                    url, 
                    loop=self.bot.loop, 
                    stream=True,
                    ffmpeg_path=self.ffmpeg_path,
                    process_playlist=False  # Не обрабатываем плейлист полностью
                )
                
                # Обновляем сообщение с результатом поиска
                await searching_message.edit(
                    content=f'✅ Добавлено в очередь: **{source.title}**{source.duration_string}'
                )
                
                # Добавляем в очередь
                await player.queue.put(source)
            
            except ValueError as e:
                await searching_message.edit(
                    content=f'❌ Ошибка: {str(e)}\n💡 Попробуйте другой трек или прямую ссылку на YouTube'
                )
                print(f"Ошибка при воспроизведении: {e}")
            
            except Exception as e:
                await searching_message.edit(
                    content=f'❌ Неожиданная ошибка: {str(e)[:100]}...\n'
                    f'💡 Попробуйте другой трек или перезапустите бота'
                )
                print(f"Подробная ошибка: {e}")
    
    @commands.command(name='playlist', help='Воспроизводит весь плейлист YouTube')
    async def playall(self, ctx, *, url):
        """Воспроизводит весь плейлист YouTube."""
        # Проверяем, подключен ли бот к голосовому каналу
        if not ctx.voice_client:
            await ctx.invoke(self.join)
        
        # Получаем плеер для этой гильдии
        player = self.get_player(ctx)
        
        # Отправляем промежуточное сообщение
        searching_message = await ctx.send("🔄 Обрабатываю плейлист...")
        
        # Обрабатываем URL плейлиста
        async with ctx.typing():
            try:
                # Проверяем, является ли это плейлистом
                is_playlist = False
                if url.startswith(('http://', 'https://')):
                    is_playlist = await YTDLSource.is_playlist(url, loop=self.bot.loop)
                
                if not is_playlist:
                    # Если это не плейлист, обрабатываем как обычный трек
                    source = await YTDLSource.from_url(
                        url, 
                        loop=self.bot.loop, 
                        stream=True,
                        ffmpeg_path=self.ffmpeg_path
                    )
                    
                    await searching_message.edit(
                        content=f'ℹ️ Это не плейлист. Добавлен трек: **{source.title}**{source.duration_string}'
                    )
                    
                    await player.queue.put(source)
                    return
                
                # Получаем все треки из плейлиста
                playlist_title, tracks = await YTDLSource.get_playlist_items(
                    url,
                    loop=self.bot.loop,
                    ffmpeg_path=self.ffmpeg_path
                )
                
                if not tracks:
                    await searching_message.edit(
                        content=f'❌ Плейлист не содержит треков или не удалось их извлечь.'
                    )
                    return
                
                # Добавляем все треки в очередь
                for track in tracks:
                    await player.queue.put(track)
                
                # Обновляем сообщение с результатом
                await searching_message.edit(
                    content=f'✅ Добавлен плейлист: **{playlist_title}** ({len(tracks)} треков)'
                )
            
            except ValueError as e:
                await searching_message.edit(
                    content=f'❌ Ошибка при обработке плейлиста: {str(e)}\n💡 Проверьте ссылку на плейлист.'
                )
                print(f"Ошибка при воспроизведении плейлиста: {e}")
            
            except Exception as e:
                await searching_message.edit(
                    content=f'❌ Неожиданная ошибка: {str(e)[:100]}...\n'
                    f'💡 Возможно, плейлист слишком большой или недоступен.'
                )
                print(f"Подробная ошибка плейлиста: {e}")
    
    @commands.command(name='pause', help='Приостанавливает текущий трек')
    async def pause(self, ctx):
        """Ставит воспроизведение на паузу."""
        voice_client = ctx.voice_client
        
        if not voice_client or not voice_client.is_playing():
            return await ctx.send("В данный момент ничего не воспроизводится.")
        
        if voice_client.is_paused():
            return await ctx.send("Трек уже на паузе.")
        
        voice_client.pause()
        await ctx.send("⏸️ Пауза")
    
    @commands.command(name='resume', help='Возобновляет воспроизведение трека')
    async def resume(self, ctx):
        """Возобновляет воспроизведение трека после паузы."""
        voice_client = ctx.voice_client
        
        if not voice_client or not voice_client.is_connected():
            return await ctx.send("Я не подключен к голосовому каналу.")
        
        if not voice_client.is_paused():
            return await ctx.send("Трек не на паузе.")
        
        voice_client.resume()
        await ctx.send("▶️ Воспроизведение")
    
    @commands.command(name='skip', help='Пропускает текущий трек')
    async def skip(self, ctx):
        """Пропускает текущий трек и переходит к следующему."""
        voice_client = ctx.voice_client
        
        if not voice_client or not voice_client.is_connected():
            return await ctx.send("Я не подключен к голосовому каналу.")
        
        if not voice_client.is_playing():
            return await ctx.send("В данный момент ничего не воспроизводится.")
        
        # Пропускаем текущий трек
        voice_client.stop()
        await ctx.send("⏭️ Трек пропущен")
    
    @commands.command(name='loop', help='Включает/выключает повтор текущего трека')
    async def toggle_loop(self, ctx):
        """Включает или выключает повтор текущего трека."""
        player = self.get_player(ctx)
        player.loop = not player.loop
        
        status = "включен" if player.loop else "выключен"
        await ctx.send(f"🔄 Повтор трека {status}")
    
    @commands.command(name='queue', help='Показывает очередь треков')
    async def queue_info(self, ctx):
        """Отображает текущую очередь треков."""
        player = self.get_player(ctx)
        
        if player.queue.empty():
            return await ctx.send("📋 Очередь пуста.")
        
        # Получаем треки из очереди без их извлечения
        queue_list = list(player.queue._queue)
        
        # Создаем строку с информацией о треках (до 10 треков)
        queue_message = "**📋 Очередь треков:**\n"
        for i, track in enumerate(queue_list[:10], 1):
            queue_message += f"{i}. {track.title}{track.duration_string}\n"
        
        if len(queue_list) > 10:
            queue_message += f"... и еще {len(queue_list) - 10} треков"
        
        await ctx.send(queue_message)
    
    @commands.command(name='now', help='Показывает текущий трек')
    async def now_playing(self, ctx):
        """Отображает информацию о текущем треке."""
        voice_client = ctx.voice_client
        
        if not voice_client or not voice_client.is_connected():
            return await ctx.send("Я не подключен к голосовому каналу.")
        
        player = self.get_player(ctx)
        if not voice_client.is_playing():
            return await ctx.send("В данный момент ничего не воспроизводится.")
        
        # Отображаем информацию о текущем треке
        source = voice_client.source
        await ctx.send(f"🎵 Сейчас играет: **{source.title}**{source.duration_string}")
    
    @commands.command(name='stop', help='Останавливает плеер и очищает очередь')
    async def stop(self, ctx):
        """Останавливает воспроизведение и очищает очередь."""
        voice_client = ctx.voice_client
        
        if not voice_client or not voice_client.is_connected():
            return await ctx.send("Я не подключен к голосовому каналу.")
        
        # Очищаем очередь и останавливаем воспроизведение
        await self.cleanup(ctx.guild)
        await ctx.send("⏹️ Воспроизведение остановлено и очередь очищена")
    
    @commands.command(name='leave', help='Отключается от голосового канала')
    async def leave(self, ctx):
        """Отключается от голосового канала."""
        voice_client = ctx.voice_client
        
        if not voice_client or not voice_client.is_connected():
            return await ctx.send("Я не подключен к голосовому каналу.")
        
        await self.cleanup(ctx.guild)
        await ctx.send("👋 До свидания!")
    
    @play.before_invoke
    async def ensure_voice(self, ctx):
        """Убеждается, что бот подключен к голосовому каналу."""
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Вы не подключены к голосовому каналу.")
                raise commands.CommandError("Автор не подключен к голосовому каналу.")