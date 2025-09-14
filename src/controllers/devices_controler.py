from src.services.device_service import listar_devices

class DeviceController:
    
    
    @staticmethod
    def listar():
        return listar_devices()