# src/services/discovery_service.py
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import ipaddress

from src.utils.network.discovery import run_enhanced_discovery
from src.models.PLC import PLC
from src.db import db

logger = logging.getLogger(__name__)

class AutoDiscoveryService:
    """
    Serviço para descoberta automática de CLPs e salvamento no banco
    """
    
    def __init__(self):
        self.industrial_confidence_threshold = 60
        self.modbus_ports = [502, 1502]
        self.siemens_ports = [102]
        self.rockwell_ports = [44818, 2222, 1911]
        self.opcua_ports = [4840, 48400, 48401]
    
    def discover_and_save_plcs(
        self, 
        target_interfaces: Optional[List[str]] = None,
        auto_activate: bool = True,
        overwrite_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Descobre CLPs na rede e os salva automaticamente no banco
        
        Args:
            target_interfaces: Interfaces específicas para scan (None = todas)
            auto_activate: Se deve ativar automaticamente os CLPs encontrados
            overwrite_existing: Se deve sobrescrever CLPs existentes
            
        Returns:
            Dict com estatísticas da descoberta
        """
        logger.info("Iniciando descoberta automática de CLPs")
        
        try:
            # 1. Executar descoberta de rede
            discovered_devices = run_enhanced_discovery(
                target_interfaces=target_interfaces,
                save_detailed=True
            )
            
            # 2. Filtrar dispositivos que são CLPs/industriais
            potential_plcs = self._filter_industrial_devices(discovered_devices)
            
            # 3. Salvar no banco de dados
            save_results = self._save_plcs_to_database(
                potential_plcs, 
                auto_activate, 
                overwrite_existing
            )
            
            # 4. Estatísticas finais
            stats = {
                'total_devices_found': len(discovered_devices),
                'potential_plcs_found': len(potential_plcs),
                'plcs_saved': save_results['saved'],
                'plcs_updated': save_results['updated'],
                'plcs_skipped': save_results['skipped'],
                'errors': save_results['errors'],
                'discovery_time': save_results.get('discovery_time', 0)
            }
            
            logger.info(f"Descoberta concluída: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erro na descoberta automática: {e}")
            return {
                'total_devices_found': 0,
                'potential_plcs_found': 0,
                'plcs_saved': 0,
                'plcs_updated': 0,
                'plcs_skipped': 0,
                'errors': 1,
                'error_message': str(e)
            }
    
    def _filter_industrial_devices(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra dispositivos que têm características de CLPs/dispositivos industriais
        """
        potential_plcs = []
        
        for device in devices:
            # Verificar se tem indicadores de dispositivo industrial
            industrial_info = device.get('industrial_device', {})
            confidence = industrial_info.get('confidence', 0)
            device_type = industrial_info.get('type', 'unknown')
            protocols = industrial_info.get('protocol', [])
            
            # Critérios para considerar como PLC
            is_potential_plc = False
            plc_type = 'device'
            primary_protocol = 'unknown'
            detected_ports = []
            
            # Analisar portas abertas
            open_ports = device.get('open_ports', {})
            services = device.get('services', {})
            
            for port in open_ports:
                if port in self.modbus_ports:
                    is_potential_plc = True
                    plc_type = 'modbus_plc'
                    primary_protocol = 'modbus_tcp'
                    detected_ports.append(port)
                    
                elif port in self.siemens_ports:
                    is_potential_plc = True
                    plc_type = 'siemens_plc'
                    primary_protocol = 's7comm'
                    detected_ports.append(port)
                    
                elif port in self.rockwell_ports:
                    is_potential_plc = True
                    plc_type = 'rockwell_plc'
                    primary_protocol = 'ethernet_ip'
                    detected_ports.append(port)
                    
                elif port in self.opcua_ports:
                    is_potential_plc = True
                    plc_type = 'opcua_plc'
                    primary_protocol = 'opcua'
                    detected_ports.append(port)
            
            # Verificar confiança do sistema de detecção
            if confidence >= self.industrial_confidence_threshold:
                is_potential_plc = True
                if plc_type == 'device':  # Se ainda não foi classificado
                    plc_type = device_type
            
            # Se identificado como PLC potencial, adicionar à lista
            if is_potential_plc:
                plc_data = {
                    'ip_address': device['ip'],
                    'mac': self._normalize_mac(device.get('mac')),
                    'network': device.get('network'),
                    'interface': device.get('interface'),
                    'detected_ports': detected_ports,
                    'primary_protocol': primary_protocol,
                    'plc_type': plc_type,
                    'confidence': confidence,
                    'protocols': protocols,
                    'responds_to_ping': device.get('responds_to_ping', False),
                    'services': services,
                    'discovery_method': device.get('discovered_via', []),
                    'discovery_timestamp': datetime.now()
                }
                
                potential_plcs.append(plc_data)
                logger.debug(f"PLC detectado: {plc_data['ip_address']} - {plc_data['plc_type']} - Confiança: {confidence}%")
        
        logger.info(f"Filtrados {len(potential_plcs)} dispositivos industriais de {len(devices)} total")
        return potential_plcs
    
    def _save_plcs_to_database(
        self, 
        plcs_data: List[Dict[str, Any]], 
        auto_activate: bool = True,
        overwrite_existing: bool = False
    ) -> Dict[str, int]:
        """
        Salva os CLPs descobertos no banco de dados
        """
        stats = {
            'saved': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for plc_data in plcs_data:
            try:
                ip_address = plc_data['ip_address']
                
                # Verificar se PLC já existe
                existing_plc = db.session.query(PLC).filter_by(ip_address=ip_address).first()
                
                if existing_plc and not overwrite_existing:
                    # Se existe e não deve sobrescrever, pular
                    if not existing_plc.manual:  # Atualizar apenas se não foi criado manualmente
                        # Atualizar alguns campos básicos
                        existing_plc.is_online = plc_data.get('responds_to_ping', False)
                        existing_plc.last_connection = datetime.now()
                        stats['updated'] += 1
                    else:
                        stats['skipped'] += 1
                    continue
                
                # Preparar dados para o PLC
                plc_name = self._generate_plc_name(plc_data)
                
                # Determinar protocolo principal
                primary_port = 502  # Default Modbus
                if plc_data['detected_ports']:
                    primary_port = plc_data['detected_ports'][0]
                
                # Criar ou atualizar PLC
                if existing_plc:
                    # Atualizar existente
                    existing_plc.name = plc_name
                    existing_plc.mac = plc_data.get('mac') or existing_plc.mac
                    existing_plc.subnet = plc_data.get('network') or existing_plc.subnet
                    existing_plc.portas = plc_data['detected_ports'] or [primary_port]
                    existing_plc.tipo = plc_data['plc_type']
                    existing_plc.protocol = self._map_protocol(plc_data['primary_protocol'])
                    existing_plc.is_active = auto_activate
                    existing_plc.is_online = plc_data.get('responds_to_ping', False)
                    existing_plc.last_connection = datetime.now()
                    existing_plc.manual = False  # Marcar como descoberto automaticamente
                    
                    stats['updated'] += 1
                    logger.info(f"PLC atualizado: {ip_address} - {plc_name}")
                    
                else:
                    # Criar novo PLC
                    new_plc = PLC(
                        name=plc_name,
                        mac=plc_data.get('mac'),
                        ip_address=ip_address,
                        subnet=plc_data.get('network'),
                        portas=plc_data['detected_ports'] or [primary_port],
                        tipo=plc_data['plc_type'],
                        protocol=self._map_protocol(plc_data['primary_protocol']),
                        unit_id=1,  # Default
                        polling_interval=1000,  # Default 1 segundo
                        timeout=3000,  # Default 3 segundos
                        is_active=auto_activate,
                        is_online=plc_data.get('responds_to_ping', False),
                        last_connection=datetime.now() if plc_data.get('responds_to_ping') else None,
                        manual=False  # Descoberto automaticamente
                    )
                    
                    db.session.add(new_plc)
                    stats['saved'] += 1
                    logger.info(f"Novo PLC salvo: {ip_address} - {plc_name}")
                
                # Commit das mudanças
                db.session.commit()
                
            except IntegrityError as e:
                db.session.rollback()
                logger.error(f"Erro de integridade ao salvar PLC {plc_data['ip_address']}: {e}")
                stats['errors'] += 1
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao salvar PLC {plc_data['ip_address']}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _generate_plc_name(self, plc_data: Dict[str, Any]) -> str:
        """Gera um nome automático para o PLC baseado nos dados descobertos"""
        ip = plc_data['ip_address']
        plc_type = plc_data.get('plc_type', 'PLC').replace('_', ' ').title()
        
        # Tentar usar fabricante se identificado
        protocols = plc_data.get('protocols', [])
        if 'modbus' in protocols:
            return f"Modbus PLC {ip}"
        elif 's7' in protocols or 'siemens' in str(protocols).lower():
            return f"Siemens PLC {ip}"
        elif 'ethernet_ip' in protocols:
            return f"Rockwell PLC {ip}"
        elif 'opcua' in protocols:
            return f"OPC-UA Device {ip}"
        else:
            return f"{plc_type} {ip}"
    
    def _normalize_mac(self, mac: Optional[str]) -> Optional[str]:
        """Normaliza endereço MAC"""
        if not mac:
            return None
        
        # Remover caracteres especiais e normalizar formato
        mac = mac.strip().lower().replace('-', ':')
        
        # Verificar formato válido
        if len(mac.replace(':', '')) == 12:
            # Reformatar para padrão xx:xx:xx:xx:xx:xx
            clean_mac = mac.replace(':', '')
            formatted_mac = ':'.join([clean_mac[i:i+2] for i in range(0, 12, 2)])
            return formatted_mac
        
        return mac if ':' in mac else None
    
    def _map_protocol(self, detected_protocol: str) -> str:
        """Mapeia protocolo detectado para formato do banco"""
        protocol_map = {
            'modbus_tcp': 'modbus_tcp',
            'modbus': 'modbus_tcp',
            's7comm': 's7_tcp',
            'ethernet_ip': 'ethernet_ip',
            'opcua': 'opcua',
            'unknown': 'modbus_tcp'  # Default
        }
        
        return protocol_map.get(detected_protocol.lower(), 'modbus_tcp')
    
    def get_discovered_plcs_summary(self) -> List[Dict[str, Any]]:
        """Retorna resumo dos PLCs descobertos automaticamente"""
        try:
            auto_plcs = db.session.query(PLC).filter_by(manual=False).all()
            
            summary = []
            for plc in auto_plcs:
                summary.append({
                    'id': plc.id,
                    'name': plc.name,
                    'ip_address': plc.ip_address,
                    'mac': plc.mac,
                    'tipo': plc.tipo,
                    'protocol': plc.protocol,
                    'portas': plc.portas,
                    'is_active': plc.is_active,
                    'is_online': plc.is_online,
                    'last_connection': plc.last_connection.isoformat() if plc.last_connection else None,
                    'created_at': plc.created_at.isoformat() if plc.created_at else None
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Erro ao obter resumo dos PLCs descobertos: {e}")
            return []
    
    def rediscover_plcs(self, plc_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Re-executa descoberta para PLCs específicos ou todos os automáticos
        """
        try:
            if plc_ids:
                # Redescobrir PLCs específicos
                target_plcs = db.session.query(PLC).filter(PLC.id.in_(plc_ids)).all()
            else:
                # Redescobrir todos os PLCs automáticos
                target_plcs = db.session.query(PLC).filter_by(manual=False).all()
            
            target_ips = [plc.ip_address for plc in target_plcs]
            
            logger.info(f"Redescoberta iniciada para {len(target_ips)} PLCs")
            
            # Executar descoberta focada nos IPs alvo
            # (aqui você pode implementar uma versão otimizada que só testa IPs específicos)
            
            return {
                'success': True,
                'plcs_checked': len(target_ips),
                'message': 'Redescoberta concluída'
            }
            
        except Exception as e:
            logger.error(f"Erro na redescoberta: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Função de conveniência para uso direto
def auto_discover_plcs(**kwargs) -> Dict[str, Any]:
    """Função de conveniência para descoberta automática de PLCs"""
    service = AutoDiscoveryService()
    return service.discover_and_save_plcs(**kwargs)