# app/utils/async_runner.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

class AsyncLoopThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coro(self, coro):
        """Agenda a coroutine e retorna concurrent.futures.Future"""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

# criar uma instância global em app/__init__.py ao criar o app
async_loop = AsyncLoopThread()
