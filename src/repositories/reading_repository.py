from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.models.Reading import Reading
from src.models.Registers import Register
from src.repositories.base_repository import BaseRepository
from sqlalchemy import and_, func, desc

class ReadingRepository(BaseRepository[Reading]):
    
    def __init__(self):
        super().__init__(Reading)
    
    def get_latest_readings(self, plc_id: int) -> List[Dict]:
        """Retorna as últimas leituras de todos os registradores de um PLC"""
        subquery = self.db.session.query(
            Reading.register_id,
            func.max(Reading.timestamp).label('latest_timestamp')
        ).join(Register).filter(
            Register.plc_id == plc_id
        ).group_by(Reading.register_id).subquery()
        
        return self.db.session.query(
            Reading, Register
        ).join(Register).join(
            subquery,
            and_(
                Reading.register_id == subquery.c.register_id,
                Reading.timestamp == subquery.c.latest_timestamp
            )
        ).all()
    
    def get_historical_data(self, register_id: int, start_time: datetime, 
                           end_time: datetime, limit: int = 1000) -> List[Reading]:
        """Retorna dados históricos de um registrador"""
        return self.db.session.query(Reading).filter(
            and_(
                Reading.register_id == register_id,
                Reading.timestamp >= start_time,
                Reading.timestamp <= end_time
            )
        ).order_by(desc(Reading.timestamp)).limit(limit).all()
    
    def get_aggregated_data(self, register_id: int, start_time: datetime, 
                           end_time: datetime, interval_minutes: int = 5) -> List[Dict]:
        """Retorna dados agregados (média, min, max) por intervalo"""
        # Agrupa por intervalos de tempo
        time_bucket = func.date_trunc('minute', Reading.timestamp)
        
        return self.db.session.query(
            time_bucket.label('time_bucket'),
            func.avg(Reading.scaled_value).label('avg_value'),
            func.min(Reading.scaled_value).label('min_value'),
            func.max(Reading.scaled_value).label('max_value'),
            func.count(Reading.id).label('count')
        ).filter(
            and_(
                Reading.register_id == register_id,
                Reading.timestamp >= start_time,
                Reading.timestamp <= end_time,
                Reading.quality == 'good'
            )
        ).group_by(time_bucket).order_by(time_bucket).all()
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove dados antigos para manter performance"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        deleted_count = self.db.session.query(Reading).filter(
            Reading.timestamp < cutoff_date
        ).delete()
        
        self.db.session.commit()
        return deleted_count
    
    def bulk_insert(self, readings: List[Reading]):
        """Inserção em lote para melhor performance"""
        self.db.session.add_all(readings)
        self.db.session.commit()
