import asyncio
from typing import Dict, List
from sqlalchemy.orm import sessionmaker
from src.models.PLC import PLC
from src.models.Registers import Register
from src.models.Reading import Reading
from src.adapters.modbus_adapter import ModbusAdapter
from src import db
import logging

logger = logging.getLogger(__name__)

class PollingService:
    
    def __init__(self):
        self.polling_tasks: Dict[int, asyncio.Task] = {}
        self.adapters: Dict[int, ModbusAdapter] = {}
        self.running = False
    
    async def start_polling(self):
        """Inicia sistema de polling para todos os PLCs ativos"""
        self.running = True
        logger.info("Sistema de polling iniciado")
        
        # Carrega PLCs ativos
        active_plcs = db.session.query(PLC).filter(PLC.is_active == True).all()
        
        for plc in active_plcs:
            await self.start_plc_polling(plc)
    
    async def start_plc_polling(self, plc: PLC):
        """Inicia polling para um PLC específico"""
        if plc.id in self.polling_tasks:
            return  # Já está rodando
        
        # Cria adapter para o PLC
        adapter = ModbusAdapter(
            ip_address=plc.ip_address,
            port=plc.port,
            unit_id=plc.unit_id,
            timeout=plc.timeout
        )
        
        self.adapters[plc.id] = adapter
        
        # Cria task de polling
        task = asyncio.create_task(self._poll_plc_loop(plc, adapter))
        self.polling_tasks[plc.id] = task
        
        logger.info(f"Polling iniciado para PLC {plc.name} ({plc.ip_address})")
    
    async def stop_plc_polling(self, plc_id: int):
        """Para polling de um PLC específico"""
        if plc_id in self.polling_tasks:
            self.polling_tasks[plc_id].cancel()
            del self.polling_tasks[plc_id]
        
        if plc_id in self.adapters:
            await self.adapters[plc_id].disconnect()
            del self.adapters[plc_id]
    
    async def _poll_plc_loop(self, plc: PLC, adapter: ModbusAdapter):
        """Loop de polling para um PLC"""
        try:
            # Conecta ao PLC
            if not await adapter.connect():
                logger.error(f"Falha ao conectar PLC {plc.name}")
                return
            
            # Atualiza status online
            plc.is_online = True
            db.session.commit()
            
            while self.running:
                try:
                    # Carrega registradores ativos do PLC
                    registers = db.session.query(Register).filter(
                        Register.plc_id == plc.id,
                        Register.is_active == True
                    ).all()
                    
                    if not registers:
                        await asyncio.sleep(plc.polling_interval / 1000.0)
                        continue
                    
                    # Prepara dados para leitura
                    reg_data = [reg.to_dict() for reg in registers]
                    
                    # Lê registradores
                    readings_data = await adapter.read_registers(reg_data)
                    
                    # Salva leituras no banco
                    await self._save_readings(readings_data, registers)
                    
                    # Aguarda próximo ciclo
                    await asyncio.sleep(plc.polling_interval / 1000.0)
                    
                except Exception as e:
                    logger.error(f"Erro no polling do PLC {plc.name}: {e}")
                    await asyncio.sleep(5)  # Aguarda antes de tentar novamente
        
        except asyncio.CancelledError:
            logger.info(f"Polling cancelado para PLC {plc.name}")
        finally:
            # Atualiza status offline
            plc.is_online = False
            db.session.commit()
            await adapter.disconnect()
    
    async def _save_readings(self, readings_data: List[Dict], registers: List[Register]):
        """Salva leituras no banco de dados"""
        readings_to_add = []
        
        for reading_data in readings_data:
            # Encontra o registrador correspondente
            register = next(
                (r for r in registers if r.id == reading_data['register_id']), 
                None
            )
            if not register:
                continue
            
            # Aplica escala e offset
            raw_value = reading_data['raw_value']
            scaled_value = (raw_value * register.scale_factor) + register.offset
            
            # Cria objeto Reading
            reading = Reading(
                register_id=register.id,
                raw_value=raw_value,
                scaled_value=scaled_value,
                quality=reading_data['quality']
            )
            
            readings_to_add.srcend(reading)
        
        # Salva em lote para performance
        if readings_to_add:
            db.session.add_all(readings_to_add)
            db.session.commit()
