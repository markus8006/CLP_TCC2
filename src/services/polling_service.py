import asyncio
from typing import Dict, List
from src.models.PLC import PLC
from src.models.Registers import Register
from src.models.Reading import Reading
from src.adapters.modbus_adapter import ModbusAdapter
from src.db import db
import logging
from src.utils.async_runner import async_loop
from flask import Flask

logger = logging.getLogger(__name__)

class PollingService:
    def __init__(self, app: Flask = None):
        """
        Recebe optionalmente a app para usar app_context.
        """
        self.app = app
        self.polling_tasks: Dict[int, asyncio.Future] = {}
        self.adapters: Dict[int, ModbusAdapter] = {}
        self.running = False

    def init_app(self, app: Flask):
        self.app = app

    async def start_polling(self):
        if not self.app:
            logger.error("PollingService precisa de app (chame init_app ou passe app no construtor).")
            return

        self.running = True
        logger.info("Sistema de polling iniciado")

        def _get_active_plcs():
            with self.app.app_context():
                return db.session.query(PLC).filter(PLC.is_active == True).all()

        active_plcs = await asyncio.to_thread(_get_active_plcs)

        for plc in active_plcs:
            await self.start_plc_polling(plc.id)

    async def start_plc_polling(self, plc_id: int):
        """Inicia polling para um PLC específico (recebe plc_id para evitar passar ORM entre threads)"""
        logger.info("Chamado start_plc_polling para PLC id=%s", plc_id)
        if plc_id in self.polling_tasks:
            logger.info("Polling já está ativo para PLC id=%s", plc_id)
            return

        # busca o objeto PLC dentro do app_context (thread-safe)
        def _get_plc():
            with self.app.app_context():
                return db.session.get(PLC, plc_id)

        plc = await asyncio.to_thread(_get_plc)
        if not plc:
            logger.error("PLC id=%s não encontrado no DB", plc_id)
            return

        try:
            logger.info("Criando adapter para PLC id=%s (ip=%s port=%s unit=%s)",
                        plc_id, plc.ip_address, plc.portas, getattr(plc, "unit_id", None))
            adapter = ModbusAdapter(
                ip_address=plc.ip_address,
                port=int(plc.portas[0]),
                timeout=plc.timeout
            )
            self.adapters[plc_id] = adapter

            # Agenda a tarefa de polling no loop global (async_loop importado no módulo)
            future = async_loop.run_coro(self._poll_plc_loop(plc_id, adapter))
            self.polling_tasks[plc_id] = future
            logger.info("Polling iniciado para PLC %s (%s) -> future=%s", plc.name, plc.ip_address, future)

        except Exception as e:
            logger.exception("Erro ao iniciar polling para PLC id=%s: %s", plc_id, e)

    async def stop_plc_polling(self, plc_id: int):
        if plc_id in self.polling_tasks:
            fut = self.polling_tasks[plc_id]
            fut.cancel()
            del self.polling_tasks[plc_id]

        if plc_id in self.adapters:
            try:
                await self.adapters[plc_id].disconnect()
            except Exception:
                logger.exception("Erro ao desconectar adapter")
            finally:
                del self.adapters[plc_id]

    async def _poll_plc_loop(self, plc_id: int, adapter: ModbusAdapter):
        logger.info(f"Leitura iniciada para PLC id={plc_id}")

        def _get_plc():
            with self.app.app_context():
                return db.session.get(PLC, plc_id)

        plc = await asyncio.to_thread(_get_plc)
        if not plc:
            logger.error(f"PLC id={plc_id} removido antes do polling iniciar")
            return

        try:
            ok = await adapter.connect()
            if not ok:
                logger.error(f"Falha ao conectar PLC {plc.name}")
                return

            def _set_online(value: bool):
                with self.app.app_context():
                    p = db.session.get(PLC, plc_id)
                    if p:
                        p.is_online = value
                        db.session.commit()

            await asyncio.to_thread(_set_online, True)

            while self.running:
                try:
                    def _get_registers():
                        with self.app.app_context():
                            return db.session.query(Register).filter(
                                Register.plc_id == plc_id,
                                Register.is_active == True
                            ).all()

                    registers = await asyncio.to_thread(_get_registers)

                    if not registers:
                        plc = await asyncio.to_thread(_get_plc)
                        await asyncio.sleep((plc.polling_interval / 1000.0) if plc else 1.0)
                        continue

                    reg_data = [reg.to_dict() for reg in registers]
                    readings_data = await adapter.read_registers(reg_data)
                    await self._save_readings(readings_data, registers)

                    plc = await asyncio.to_thread(_get_plc)
                    await asyncio.sleep((plc.polling_interval / 1000.0) if plc else 1.0)

                except asyncio.CancelledError:
                    logger.info(f"Polling cancelado internamente para PLC id={plc_id}")
                    raise
                except Exception as e:
                    logger.exception(f"Erro no polling do PLC id={plc_id}: {e}")
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info(f"Polling cancelado para PLC id={plc_id}")
        finally:
            def _set_offline():
                with self.app.app_context():
                    p = db.session.get(PLC, plc_id)
                    if p:
                        p.is_online = False
                        db.session.commit()

            await asyncio.to_thread(_set_offline)
            try:
                await adapter.disconnect()
            except Exception:
                logger.exception("Erro ao desconectar adapter no finally")

    async def _save_readings(self, readings_data: List[Dict], registers: List[Register]):
        def _save():
            with self.app.app_context():
                readings_to_add = []
                for reading_data in readings_data:
                    register = next((r for r in registers if r.id == reading_data['register_id']), None)
                    if not register:
                        continue
                    raw_value = reading_data['raw_value']
                    scaled_value = (raw_value * register.scale_factor) + register.offset
                    reading = Reading(
                        register_id=register.id,
                        raw_value=raw_value,
                        scaled_value=scaled_value,
                        quality=reading_data.get('quality')
                    )
                    readings_to_add.append(reading)

                if readings_to_add:
                    db.session.add_all(readings_to_add)
                    db.session.commit()

        await asyncio.to_thread(_save)
