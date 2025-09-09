import aiohttp
import asyncio


class Stats:
    def __init__(self, bot, logger=None, TOPGG_TOKEN='', DISCORDBOTS_TOKEN='',
                 DISCORDBOTLISTCOM_TOKEN='', DISCORDLIST_TOKEN=''):
        self.bot = bot
        self.logger = logger
        self.TOPGG_TOKEN = TOPGG_TOKEN
        self.DISCORDBOTS_TOKEN = DISCORDBOTS_TOKEN
        self.DISCORDBOTLISTCOM_TOKEN = DISCORDBOTLISTCOM_TOKEN
        self.DISCORDLIST_TOKEN = DISCORDLIST_TOKEN

        self._tasks = []

    async def _post_stats(self, url, headers, json_data):
        """Post statistics to a given URL with error logging."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=json_data) as resp:
                    if resp.status != 200 and self.logger:
                        text = await resp.text()
                        self.logger.error(f'Failed to update {url}: {resp.status} {text}')
        except Exception as e:
            if self.logger:
                self.logger.error(f'Exception while posting stats to {url}: {e}')

    async def _loop_post(self, url, headers, json_func, interval=60*30):
        """Generic loop for posting stats periodically."""
        while True:
            try:
                json_data = json_func()
                await self._post_stats(url, headers, json_data)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f'Exception in stats loop for {url}: {e}')
                await asyncio.sleep(interval)

    def _topgg_data(self):
        return {'server_count': len(self.bot.guilds), 'shard_count': len(self.bot.shards)}

    def _discordbots_data(self):
        return {'guildCount': len(self.bot.guilds), 'shardCount': len(self.bot.shards)}

    def _discordbotlist_com_data(self):
        return {'guilds': len(self.bot.guilds),
                'users': sum(guild.member_count for guild in self.bot.guilds)}

    def _discordlist_data(self):
        return {'count': len(self.bot.guilds)}

    def start_stats_update(self):
        """Start all stats update tasks in parallel."""
        if self.TOPGG_TOKEN:
            url = f'https://top.gg/api/bots/{self.bot.user.id}/stats'
            headers = {'Authorization': self.TOPGG_TOKEN, 'Content-Type': 'application/json'}
            self._tasks.append(asyncio.create_task(self._loop_post(url, headers, self._topgg_data)))

        if self.DISCORDBOTS_TOKEN:
            url = f'https://discord.bots.gg/api/v1/bots/{self.bot.user.id}/stats'
            headers = {'Authorization': self.DISCORDBOTS_TOKEN, 'Content-Type': 'application/json'}
            self._tasks.append(asyncio.create_task(self._loop_post(url, headers, self._discordbots_data)))

        if self.DISCORDBOTLISTCOM_TOKEN:
            url = f'https://discordbotlist.com/api/v1/bots/{self.bot.user.id}/stats'
            headers = {'Authorization': self.DISCORDBOTLISTCOM_TOKEN, 'Content-Type': 'application/json'}
            self._tasks.append(asyncio.create_task(self._loop_post(url, headers, self._discordbotlist_com_data)))

        if self.DISCORDLIST_TOKEN:
            url = f'https://api.discordlist.gg/v0/bots/{self.bot.user.id}/guilds'
            headers = {'Authorization': f'Bearer {self.DISCORDLIST_TOKEN}', 'Content-Type': 'application/json; charset=utf-8'}
            self._tasks.append(asyncio.create_task(self._loop_post(url, headers, self._discordlist_data)))

        return self._tasks

    async def stop_stats_update(self):
        """Cancel all running stats update tasks."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()


if __name__ == '__main__':
    print('This is a module. Do not run it directly.')
