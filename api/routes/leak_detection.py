"""
API routes cho leak detection
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from services.leak_detection_service import leak_detection_service
from utils.logger import logger

router = APIRouter()

class LeakDetectionRequest(BaseModel):
    """Request để detect leak từ simulation results"""
    nodes_data: Dict[str, List[Dict[str, Any]]]
    threshold: Optional[float] = None

class LeakDetectionFromSimulationRequest(BaseModel):
    """Request để detect leak từ simulation result"""
    simulation_result: Dict[str, Any]
    threshold: Optional[float] = None

@router.get("/status")
async def get_leak_detection_status():
    """
    Kiểm tra trạng thái của leak detection service
    """
    is_ready = leak_detection_service.is_ready()
    
    return {
        "success": True,
        "ready": is_ready,
        "message": "Service ready" if is_ready else "Service not ready - model not loaded",
        "threshold": leak_detection_service.threshold if is_ready else None
    }

@router.post("/detect")
async def detect_leaks(request: LeakDetectionRequest):
    """
    Detect leaks từ nodes data
    
    - **nodes_data**: Dict với key là node_id, value là list of records
                      Mỗi record có: timestamp, pressure, head, demand
    - **threshold**: Optional threshold override (default: use model threshold)
    """
    try:
        if not leak_detection_service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Leak detection service not ready - model not loaded"
            )
        
        result = leak_detection_service.detect_leaks(
            nodes_data=request.nodes_data,
            threshold=request.threshold
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Leak detection failed")
            )
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in detect_leaks endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error detecting leaks: {str(e)}"
        )

@router.post("/detect-from-simulation")
async def detect_leaks_from_simulation(request: LeakDetectionFromSimulationRequest):
    """
    Detect leaks từ simulation result
    
    - **simulation_result**: SimulationResult dict từ EPANET service
    - **threshold**: Optional threshold override
    """
    try:
        if not leak_detection_service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Leak detection service not ready - model not loaded"
            )
        
        result = leak_detection_service.detect_leaks_from_simulation_result(
            simulation_result=request.simulation_result,
            threshold=request.threshold
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Leak detection failed")
            )
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in detect_leaks_from_simulation endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error detecting leaks: {str(e)}"
        )



