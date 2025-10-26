from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class NodeData(BaseModel):
    node_id: Optional[str] = Field(None, description="ID của nút trong mạng lưới (có thể None cho SCADA boundary conditions)")
    pressure: Optional[float] = Field(None, description="Áp lực tại nút (m)")
    flow: Optional[float] = Field(None, description="Lưu lượng qua nút (LPS)")
    demand: Optional[float] = Field(None, description="Nhu cầu nước tại nút (LPS)")
    head: Optional[float] = Field(None, description="Cột áp tại nút (m)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RealTimeDataInput(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now, description="Thời gian đo")
    nodes: List[NodeData] = Field(..., description="Dữ liệu các nút")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SimulationInput(BaseModel):
    duration: int = Field(24, description="Thời gian mô phỏng (giờ)")
    hydraulic_timestep: int = Field(1, description="Bước thời gian thủy lực (giờ)")
    report_timestep: int = Field(1, description="Bước thời gian báo cáo (giờ)")
    real_time_data: Optional[RealTimeDataInput] = Field(None, description="Dữ liệu thời gian thực")
    demand_multiplier: float = Field(1.0, description="Hệ số nhân nhu cầu")
    
class SimulationResult(BaseModel):
    run_id: int
    status: SimulationStatus
    timestamp: datetime
    duration: float
    nodes_results: Dict[str, List[Dict[str, Any]]]  # Changed from NodeData to Dict
    pipes_results: Dict[str, List[Dict[str, Any]]]
    pumps_results: Dict[str, List[Dict[str, Any]]]
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SimulationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[SimulationResult] = None

class NodePressureRequest(BaseModel):
    node_id: str = Field(..., description="ID của nút")
    pressure: float = Field(..., description="Áp lực đo được (m)")
    timestamp: datetime = Field(default_factory=datetime.now)

class NodeFlowRequest(BaseModel):
    node_id: str = Field(..., description="ID của nút")
    flow: float = Field(..., description="Lưu lượng đo được (LPS)")
    timestamp: datetime = Field(default_factory=datetime.now)

class BulkDataInput(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    pressure_data: List[NodePressureRequest] = Field(..., description="Dữ liệu áp lực")
    flow_data: List[NodeFlowRequest] = Field(..., description="Dữ liệu lưu lượng")

class NetworkStatus(BaseModel):
    total_nodes: int
    total_pipes: int
    total_pumps: int
    total_reservoirs: int
    simulation_running: bool
    last_simulation_time: Optional[datetime] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None
