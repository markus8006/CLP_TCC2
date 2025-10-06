import asyncio
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from typing import List, Dict, Any
from .protocol_interface import ProtocolAdapter
import logging

logger = logging.getLogger(__name__)

class ModbusAdapter(ProtocolAdapter):
    
    def __init__(self, ip_address: str, port: int = 502, unit_id: int = 1, timeout: int = 3):
        self.ip_address = ip_address
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.client = None
        self._connected = False
    
    async def connect(self) -> bool:
        try:
            self.client = AsyncModbusTcpClient(
                host=self.ip_address,
                port=self.port,
                timeout=self.timeout
            )
            await self.client.connect()
            self._connected = True
            logger.info(f"Conectado ao PLC {self.ip_address}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar PLC {self.ip_address}: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        if self.client:
            self.client.close()
            self._connected = False
    
    async def read_registers(self, registers: List[Dict]) -> List[Dict]:
        if not self.is_connected():
            return []
        
        results = []
        for reg in registers:
            try:
                address = reg['address']
                register_type = reg['register_type']
                data_type = reg['data_type']
                
                # Leitura baseada no tipo de registrador
                if register_type == 'holding':
                    result = await self.client.read_holding_registers(
                        address, 1, unit=self.unit_id
                    )
                elif register_type == 'input':
                    result = await self.client.read_input_registers(
                        address, 1, unit=self.unit_id
                    )
                elif register_type == 'coil':
                    result = await self.client.read_coils(
                        address, 1, unit=self.unit_id
                    )
                
                if not result.isError():
                    raw_value = self._convert_value(result.registers[0], data_type)
                    results.append({
                        'register_id': reg['id'],
                        'raw_value': raw_value,
                        'quality': 'good',
                        'timestamp': asyncio.get_event_loop().time()
                    })
                else:
                    results.append({
                        'register_id': reg['id'],
                        'raw_value': 0,
                        'quality': 'bad',
                        'timestamp': asyncio.get_event_loop().time()
                    })
                    
            except Exception as e:
                logger.error(f"Erro lendo registrador {reg['address']}: {e}")
                results.append({
                    'register_id': reg['id'],
                    'raw_value': 0,
                    'quality': 'bad',
                    'timestamp': asyncio.get_event_loop().time()
                })
        
        return results
    
    def _convert_value(self, raw_value: int, data_type: str) -> float:
        """Converte valor bruto conforme tipo de dado"""
        if data_type == 'int16':
            # Converte para signed int16
            if raw_value > 32767:
                return raw_value - 65536
            return raw_value
        elif data_type == 'float32':
            # Implementar conversão IEEE 754
            pass
        elif data_type == 'bool':
            return float(bool(raw_value))
        else:  # uint16
            return float(raw_value)
    
    async def write_register(self, address: int, value: Any) -> bool:
        # Implementar escrita se necessário
        pass
    
    def is_connected(self) -> bool:
        return self._connected and self.client is not None
