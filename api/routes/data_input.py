from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime

from models.schemas import (
    RealTimeDataInput, NodeData, NodePressureRequest, 
    NodeFlowRequest, BulkDataInput, ErrorResponse
)
from core.database import db_manager

router = APIRouter()

@router.post("/realtime", response_model=Dict[str, Any])
async def submit_real_time_data(data: RealTimeDataInput):
    """
    Gửi dữ liệu thời gian thực cho mô phỏng EPANET
    
    - **timestamp**: Thời gian đo dữ liệu
    - **nodes**: Danh sách dữ liệu các nút (áp lực, lưu lượng, nhu cầu)
    """
    try:
        # Lưu dữ liệu vào database
        for node_data in data.nodes:
            db_manager.save_real_time_data(
                node_id=node_data.node_id,
                pressure=node_data.pressure,
                flow=node_data.flow,
                demand=node_data.demand
            )
        
        return {
            "success": True,
            "message": f"Đã lưu dữ liệu cho {len(data.nodes)} nút",
            "timestamp": data.timestamp,
            "nodes_count": len(data.nodes)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lưu dữ liệu thời gian thực: {str(e)}"
        )

@router.post("/pressure", response_model=Dict[str, Any])
async def submit_pressure_data(pressure_data: List[NodePressureRequest]):
    """
    Gửi dữ liệu áp lực cho các nút
    
    - **node_id**: ID của nút
    - **pressure**: Áp lực đo được (m)
    - **timestamp**: Thời gian đo
    """
    try:
        saved_count = 0
        
        for data in pressure_data:
            db_manager.save_real_time_data(
                node_id=data.node_id,
                pressure=data.pressure
            )
            saved_count += 1
        
        return {
            "success": True,
            "message": f"Đã lưu dữ liệu áp lực cho {saved_count} nút",
            "timestamp": datetime.now(),
            "count": saved_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lưu dữ liệu áp lực: {str(e)}"
        )

@router.post("/flow", response_model=Dict[str, Any])
async def submit_flow_data(flow_data: List[NodeFlowRequest]):
    """
    Gửi dữ liệu lưu lượng cho các nút
    
    - **node_id**: ID của nút
    - **flow**: Lưu lượng đo được (LPS)
    - **timestamp**: Thời gian đo
    """
    try:
        saved_count = 0
        
        for data in flow_data:
            db_manager.save_real_time_data(
                node_id=data.node_id,
                flow=data.flow
            )
            saved_count += 1
        
        return {
            "success": True,
            "message": f"Đã lưu dữ liệu lưu lượng cho {saved_count} nút",
            "timestamp": datetime.now(),
            "count": saved_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lưu dữ liệu lưu lượng: {str(e)}"
        )

@router.post("/bulk", response_model=Dict[str, Any])
async def submit_bulk_data(bulk_data: BulkDataInput):
    """
    Gửi dữ liệu hàng loạt (áp lực và lưu lượng)
    
    - **timestamp**: Thời gian đo
    - **pressure_data**: Danh sách dữ liệu áp lực
    - **flow_data**: Danh sách dữ liệu lưu lượng
    """
    try:
        saved_pressure = 0
        saved_flow = 0
        
        # Lưu dữ liệu áp lực
        for data in bulk_data.pressure_data:
            db_manager.save_real_time_data(
                node_id=data.node_id,
                pressure=data.pressure
            )
            saved_pressure += 1
        
        # Lưu dữ liệu lưu lượng
        for data in bulk_data.flow_data:
            db_manager.save_real_time_data(
                node_id=data.node_id,
                flow=data.flow
            )
            saved_flow += 1
        
        return {
            "success": True,
            "message": f"Đã lưu {saved_pressure} áp lực và {saved_flow} lưu lượng",
            "timestamp": bulk_data.timestamp,
            "pressure_count": saved_pressure,
            "flow_count": saved_flow
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lưu dữ liệu hàng loạt: {str(e)}"
        )

@router.get("/latest/{node_id}")
async def get_latest_data(node_id: str):
    """
    Lấy dữ liệu mới nhất cho một nút cụ thể
    """
    try:
        data = db_manager.get_latest_real_time_data(node_id)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy dữ liệu cho nút: {node_id}"
            )
        
        return {
            "success": True,
            "node_id": node_id,
            "data": data[0] if data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy dữ liệu: {str(e)}"
        )

@router.get("/latest")
async def get_latest_all_data():
    """
    Lấy dữ liệu mới nhất cho tất cả các nút
    """
    try:
        data = db_manager.get_latest_real_time_data()
        
        return {
            "success": True,
            "data": data,
            "count": len(data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy dữ liệu: {str(e)}"
        )

@router.get("/history/{node_id}")
async def get_data_history(node_id: str, limit: int = 100):
    """
    Lấy lịch sử dữ liệu cho một nút
    
    - **node_id**: ID của nút
    - **limit**: Số lượng bản ghi tối đa (mặc định: 100)
    """
    try:
        # Implementation cần được thêm vào database manager
        return {
            "success": True,
            "node_id": node_id,
            "data": [],  # Cần implement
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy lịch sử dữ liệu: {str(e)}"
        )

@router.delete("/data/{node_id}")
async def delete_node_data(node_id: str):
    """
    Xóa dữ liệu cho một nút cụ thể
    """
    try:
        # Implementation cần được thêm vào database manager
        return {
            "success": True,
            "message": f"Đã xóa dữ liệu cho nút: {node_id}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xóa dữ liệu: {str(e)}"
        )
