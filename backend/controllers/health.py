from typing import Dict


class HealthController:
    @staticmethod
    def get_health() -> Dict[str, str]:
        return {"status": "healthy", "message": "Server is running"}
