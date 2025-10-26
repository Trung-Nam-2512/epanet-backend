from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Settings
    api_title: str = "EPANET Water Network Simulation API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # Database Settings
    database_url: Optional[str] = None
    
    # EPANET Settings
    epanet_input_file: str = "epanetVip1.inp"
    simulation_duration: int = 24  # hours
    hydraulic_timestep: int = 1   # hours
    report_timestep: int = 1       # hours
    
    # File paths
    data_dir: str = "data"
    results_dir: str = "results"
    
    # SCADA Settings
    scada_api_url: str = "https://scada.nuocngamsaigon.com/scada-api/api/station/GetStationDataByHour"
    scada_token: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1bmlxdWVfbmFtZSI6Im5uc2ciLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgLzA2L2lkZW50aXR5L2NsYWltcy91c2VyZGF0YSI6IlQzOFlNM2pUUnhnUm00U004UGhjZ3FBPTE9IiwibmJmIjoxNzYwNTI1MzE1LCJleHAiOjE3NjMyMDM3MTUsImlhdCI6MTc2MDUyNTMxNX0.ddpgC_L7C6shfUYYorGmf6RJO9v-C0yfj7r5QXW7rk"
    
    # Optional settings (ignore extra fields)
    mapbox_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields

settings = Settings()
