import random
import time
from datetime import datetime

class IoTSensor:
    def __init__(self, product_id, product_type):
        self.product_id = product_id
        self.product_type = product_type
        self.base_temperature = self.get_base_temp(product_type)
        self.base_humidity = self.get_base_humidity(product_type)

    def get_base_temp(self, product_type):
        temps = {
            "Dairy": 4,
            "Meat": 2,
            "Produce": 10,
            "Frozen": -18
        }
        return temps.get(product_type, 15)

    def get_base_humidity(self, product_type):
        humidities = {
            "Dairy": 85,
            "Meat": 90,
            "Produce": 95,
            "Frozen": 30
        }
        return humidities.get(product_type, 50)

    def read_sensors(self):
        # Simulate slight variations
        temperature = round(self.base_temperature + random.uniform(-1, 2.5), 2)
        humidity = round(self.base_humidity + random.uniform(-3, 3), 2)
        freshness_score = 100 - (abs(temperature - self.base_temperature) * 5)
        freshness_score = max(0, min(100, round(freshness_score, 2)))

        status = "Optimal"
        if temperature > self.base_temperature + 2:
            status = "Warning - Critical Temp"
        elif temperature > self.base_temperature + 1:
            status = "Elevated Temp"

        return {
            "product_id": self.product_id,
            "product_type": self.product_type,
            "temperature": temperature,
            "humidity": humidity,
            "freshness_score": freshness_score,
            "status": status,
            "location": self.simulate_gps(),
            "timestamp": time.time()
        }

    def simulate_gps(self):
        # Simple simulated GPS within a logistics route
        return {
            "lat": round(40.7128 + random.uniform(-0.1, 0.1), 4),
            "lng": round(-74.0060 + random.uniform(-0.1, 0.1), 4)
        }
