from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from services.scada_service import scada_service
from models.schemas import RealTimeDataInput, NodeData
from utils.logger import logger

router = APIRouter()

class SCADARequest(BaseModel):
    station_codes: List[str]
    from_date: str
    to_date: str

class SCADATimeRangeRequest(BaseModel):
    station_codes: List[str]
    hours_back: int = 24

@router.post("/data", response_model=Dict[str, Any])
async def get_scada_data(request: SCADARequest):
    """
    Lay du lieu tu API SCADA theo thoi gian cu the
    
    - **station_codes**: Danh sach ma tram SCADA
    - **from_date**: Ngay bat dau (format: "2025-10-22 00:00")
    - **to_date**: Ngay ket thuc (format: "2025-10-24 00:00")
    """
    try:
        logger.api_request("POST", "/scada/data", 200)
        
        result = scada_service.get_multiple_stations_data(
            station_codes=request.station_codes,
            from_date=request.from_date,
            to_date=request.to_date
        )
        
        return {
            "success": result["success"],
            "message": f"Retrieved data from {result['summary']['successful']}/{result['summary']['total_stations']} stations",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error getting SCADA data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting SCADA data: {str(e)}"
        )

@router.post("/data-by-hours", response_model=Dict[str, Any])
async def get_scada_data_by_hours(request: SCADATimeRangeRequest):
    """
    Lay du lieu SCADA theo so gio lui lai tu hien tai
    
    - **station_codes**: Danh sach ma tram SCADA
    - **hours_back**: So gio lui lai tu hien tai (mac dinh: 24)
    """
    try:
        logger.api_request("POST", "/scada/data-by-hours", 200)
        
        result = scada_service.get_realtime_data_for_epanet(
            station_codes=request.station_codes,
            hours_back=request.hours_back
        )
        
        return {
            "success": result["success"],
            "message": f"Du lieu SCADA tu {result['summary']['stations_processed']} tram - boundary conditions only",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error getting SCADA data by hours: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting SCADA data by hours: {str(e)}"
        )

@router.post("/realtime", response_model=Dict[str, Any])
async def get_scada_realtime_data(request: SCADATimeRangeRequest):
    """
    Lay du lieu thoi gian thuc tu SCADA cho mo phong EPANET
    
    - **station_codes**: Danh sach ma tram SCADA
    - **hours_back**: So gio lui lai tu hien tai (mac dinh: 24)
    """
    try:
        logger.api_request("POST", "/scada/realtime", 200)
        
        result = scada_service.get_realtime_data_for_epanet(
            station_codes=request.station_codes,
            hours_back=request.hours_back
        )
        
        return {
            "success": result["success"],
            "message": f"Du lieu thoi gian thuc tu {result['summary']['stations_processed']} tram",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting real-time data: {str(e)}"
        )

@router.get("/stations")
async def get_available_stations():
    """
    Lay danh sach cac tram SCADA co san
    """
    try:
        # Danh sach cac tram da duoc mapping
        stations = list(scada_service.station_mapping.keys())
        
        return {
            "success": True,
            "message": f"Co {len(stations)} tram SCADA",
            "stations": [
                {
                    "station_code": station_code,
                    "epanet_node": scada_service.station_mapping[station_code],
                    "description": f"Tram {station_code} -> Nut {scada_service.station_mapping[station_code]}"
                }
                for station_code in stations
            ]
        }
        
    except Exception as e:
        logger.error(f" Loi lay danh sach tram: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Loi khi lay danh sach tram: {str(e)}"
        )

@router.post("/convert-to-epanet", response_model=Dict[str, Any])
async def convert_scada_to_epanet_format(request: SCADARequest):
    """
    Chuyen doi du lieu SCADA sang dinh dang EPANET
    
    - **station_codes**: Danh sach ma tram SCADA
    - **from_date**: Ngay bat dau
    - **to_date**: Ngay ket thuc
    """
    try:
        logger.api_request("POST", "/scada/convert-to-epanet", 200)
        
        # Lay du lieu SCADA
        scada_result = scada_service.get_multiple_stations_data(
            station_codes=request.station_codes,
            from_date=request.from_date,
            to_date=request.to_date
        )
        
        # Chuyen doi sang dinh dang EPANET
        epanet_data = {}
        total_records = 0
        
        for station_code, result in scada_result["results"].items():
            if result["success"]:
                # Parse du lieu SCADA
                parsed_data = scada_service.parse_scada_data(result["data"])
                
                # Chuyen doi sang dinh dang EPANET
                epanet_formatted = scada_service.convert_to_epanet_format(parsed_data, station_code)
                
                if epanet_formatted:
                    epanet_data[station_code] = epanet_formatted
                    total_records += len(epanet_formatted)
        
        return {
            "success": len(epanet_data) > 0,
            "message": f"Chuyen doi {total_records} ban ghi tu {len(epanet_data)} tram",
            "epanet_data": epanet_data,
            "summary": {
                "stations_converted": len(epanet_data),
                "total_records": total_records
            }
        }
        
    except Exception as e:
        logger.error(f" Loi chuyen doi du lieu: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Loi khi chuyen doi du lieu: {str(e)}"
        )

class SimulationWithRealtimeRequest(BaseModel):
    station_codes: List[str]
    hours_back: int = 24
    duration: int = 24
    hydraulic_timestep: int = 1
    report_timestep: int = 1

@router.post("/simulation-with-realtime")
async def run_simulation_with_scada_data(request: SimulationWithRealtimeRequest):
    """
    Chay mo phong EPANET voi du lieu thoi gian thuc tu SCADA
    
    - **station_codes**: Danh sach ma tram SCADA
    - **hours_back**: So gio lui lai tu hien tai
    - **duration**: Thoi gian mo phong
    - **hydraulic_timestep**: Buoc thoi gian thuy luc
    - **report_timestep**: Buoc thoi gian bao cao
    """
    try:
        logger.api_request("POST", "/scada/simulation-with-realtime", 200)
        
        # Lay du lieu thoi gian thuc tu SCADA
        scada_result = scada_service.get_realtime_data_for_epanet(
            station_codes=request.station_codes,
            hours_back=request.hours_back
        )
        
        if not scada_result["success"]:
            raise HTTPException(
                status_code=400,
                detail="Khong the lay du lieu tu SCADA"
            )
        
        # ✅ TRUYỀN TRỰC TIẾP SCADA BOUNDARY DATA VÀO SIMULATION
        # Giữ nguyên boundary_conditions dict để có station_code mapping
        scada_boundary_data = scada_result.get("boundary_conditions", {})
        
        # Tao SimulationInput (không cần RealTimeDataInput nữa vì dùng scada_boundary_data trực tiếp)
        from models.schemas import SimulationInput
        simulation_input = SimulationInput(
            duration=request.duration,
            hydraulic_timestep=request.hydraulic_timestep,
            report_timestep=request.report_timestep,
            real_time_data=None,  # Không dùng nữa, dùng scada_boundary_data trực tiếp
            demand_multiplier=1.0
        )
        
        # Chay mo phong EPANET với SCADA boundary data
        from services.epanet_service import epanet_service
        try:
            logger.info(f"Running simulation with {len(scada_boundary_data)} SCADA stations")
            logger.info(f"SCADA boundary data keys: {list(scada_boundary_data.keys())}")
            simulation_result = epanet_service.run_simulation(
                simulation_input,
                scada_boundary_data=scada_boundary_data  # ✅ Truyền SCADA boundary data
            )
            logger.info(f"Simulation completed with status: {simulation_result.status}")
            if simulation_result.status == "failed":
                logger.error(f"Simulation failed: {simulation_result.error_message}")
        except Exception as sim_error:
            import traceback
            logger.error(f"Error in epanet_service.run_simulation: {str(sim_error)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        return {
            "success": simulation_result.status == "completed",
            "message": f"Simulation with SCADA data from {len(request.station_codes)} stations",
            "simulation_result": simulation_result,
            "scada_summary": scada_result["summary"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error running simulation with SCADA data: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running simulation with SCADA data: {str(e)}"
        )

class SimulationWithCustomTimeRequest(BaseModel):
    station_codes: List[str]
    from_date: str
    to_date: str
    duration: int = 24
    hydraulic_timestep: int = 1
    report_timestep: int = 1

@router.post("/simulation-with-custom-time")
async def run_simulation_with_custom_time(request: SimulationWithCustomTimeRequest):
    """
    Chay mo phong EPANET voi du lieu SCADA theo thoi gian tuy chinh
    
    - **station_codes**: Danh sach ma tram SCADA
    - **from_date**: Ngay bat dau (format: "2025-10-22 00:00")
    - **to_date**: Ngay ket thuc (format: "2025-10-24 00:00")
    - **duration**: Thoi gian mo phong
    - **hydraulic_timestep**: Buoc thoi gian thuy luc
    - **report_timestep**: Buoc thoi gian bao cao
    """
    try:
        logger.api_request("POST", "/scada/simulation-with-custom-time", 200)
        
        # Lay du lieu SCADA theo thoi gian tuy chinh
        scada_result = scada_service.get_multiple_stations_data(
            station_codes=request.station_codes,
            from_date=request.from_date,
            to_date=request.to_date
        )
        
        if not scada_result["success"]:
            raise HTTPException(
                status_code=400,
                detail="Khong the lay du lieu tu SCADA"
            )
        
        # Xu ly va chuyen doi du lieu
        epanet_data = {}
        for station_code, result in scada_result["results"].items():
            if result["success"]:
                # Parse du lieu SCADA
                parsed_data = scada_service.parse_scada_data(result["data"])
                
                # Chuyen doi sang dinh dang EPANET
                epanet_formatted = scada_service.convert_to_epanet_format(parsed_data, station_code)
                
                if epanet_formatted:
                    epanet_data[station_code] = epanet_formatted
        
        # ✅ TRUYỀN TRỰC TIẾP SCADA BOUNDARY DATA VÀO SIMULATION
        # Convert epanet_data thành format boundary_conditions (giữ station_code)
        scada_boundary_data = {}
        for station_code, epanet_data_list in epanet_data.items():
            # Format: list of dicts với timestamp, pressure, flow
            boundary_records = []
            for record in epanet_data_list:
                boundary_records.append({
                    "timestamp": record.get("timestamp"),
                    "pressure": record.get("pressure"),
                    "flow": record.get("flow"),
                    "station_code": station_code
                })
            scada_boundary_data[station_code] = boundary_records
        
        # Tao SimulationInput
        from models.schemas import SimulationInput
        simulation_input = SimulationInput(
            duration=request.duration,
            hydraulic_timestep=request.hydraulic_timestep,
            report_timestep=request.report_timestep,
            real_time_data=None,  # Không dùng nữa, dùng scada_boundary_data trực tiếp
            demand_multiplier=1.0
        )
        
        # Chay mo phong EPANET với SCADA boundary data
        from services.epanet_service import epanet_service
        simulation_result = epanet_service.run_simulation(
            simulation_input,
            scada_boundary_data=scada_boundary_data  # ✅ Truyền SCADA boundary data
        )
        
        return {
            "success": simulation_result.status == "completed",
            "message": f"Simulation with SCADA data from {request.from_date} to {request.to_date}",
            "simulation_result": simulation_result,
            "scada_summary": {
                "stations_processed": len(epanet_data),
                "total_records": sum(len(data) for data in epanet_data.values()),
                "time_range": f"{request.from_date} to {request.to_date}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error running simulation with custom time SCADA data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running simulation with custom time SCADA data: {str(e)}"
        )

@router.get("/test-connection")
async def test_scada_connection():
    """
    Test ket noi voi API SCADA
    """
    try:
        # Test voi mot tram mau
        test_station = "13085"
        now = datetime.now()
        from_date = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        to_date = now.strftime("%Y-%m-%d %H:%M")
        
        result = scada_service.get_station_data_by_hour(
            station_code=test_station,
            from_date=from_date,
            to_date=to_date
        )
        
        return {
            "success": result["success"],
            "message": f"Test ket noi SCADA voi tram {test_station}",
            "connection_status": "OK" if result["success"] else "FAILED",
            "test_result": result
        }
        
    except Exception as e:
        logger.error(f" Loi test ket noi SCADA: {str(e)}")
        return {
            "success": False,
            "message": f"Loi test ket noi: {str(e)}",
            "connection_status": "FAILED"
        }
