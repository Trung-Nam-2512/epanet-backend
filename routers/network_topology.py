"""
Network Topology API - Cung cấp dữ liệu topology cho frontend
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
import wntr
from services.network_parser import network_parser
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/network", tags=["network"])

@router.get("/topology")
async def get_network_topology() -> Dict[str, Any]:
    """
    Lấy network topology từ EPANET input file
    
    Returns:
        Dict chứa nodes và pipes với tọa độ thật
    """
    try:
        logger.info("Parsing network topology from EPANET input file")
        
        # Parse file EPANET
        result = network_parser.parse_file()
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Error parsing EPANET file: {result.get('error', 'Unknown error')}"
            )
        
        logger.info(f"Successfully parsed {result['total_nodes']} nodes and {result['total_pipes']} pipes")
        
        return {
            "success": True,
            "message": "Network topology loaded successfully",
            "data": {
                "nodes": result["nodes"],
                "pipes": result["pipes"],
                "summary": {
                    "total_nodes": result["total_nodes"],
                    "total_pipes": result["total_pipes"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting network topology: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting network topology: {str(e)}"
        )

@router.get("/topology/summary")
async def get_network_summary() -> Dict[str, Any]:
    """
    Lấy summary của network topology
    
    Returns:
        Dict chứa thông tin tổng quan
    """
    try:
        result = network_parser.parse_file()
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Error parsing EPANET file: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "success": True,
            "summary": {
                "total_nodes": result["total_nodes"],
                "total_pipes": result["total_pipes"],
                "file_path": network_parser.inp_file_path,
                "status": "loaded"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting network summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting network summary: {str(e)}"
        )

@router.get("/graph")
async def get_network_graph():
    """Get network graph structure in Cytoscape.js format
    
    Returns nodes and edges formatted for Cytoscape visualization
    """
    try:
        result = network_parser.get_graph_structure()
        
        return {
            "success": result.get("success"),
            "message": "Network graph structure loaded successfully",
            "data": {
                "nodes": result.get("nodes", []),
                "edges": result.get("edges", []),
                "summary": {
                    "total_nodes": result.get("total_nodes", 0),
                    "total_edges": result.get("total_edges", 0)
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting graph structure: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "data": {"nodes": [], "edges": []}
        }

@router.get("/patterns")
async def get_demand_patterns() -> Dict[str, Any]:
    """
    Lấy demand patterns từ EPANET input file (chỉ để hiển thị)
    
    Returns:
        Dict chứa pattern data cho frontend hiển thị
    """
    try:
        logger.info("Getting demand patterns from EPANET input file")
        
        # Load EPANET model
        wn = wntr.network.WaterNetworkModel(settings.epanet_input_file)
        
        # ✅ Apply same pattern logic as simulation: Set multipliers to 1.0
        # This ensures consistency between simulation and pattern API
        for pattern_id in wn.pattern_name_list:
            pattern = wn.get_pattern(pattern_id)
            pattern.multipliers = [1.0] * len(pattern.multipliers)
            logger.info(f"Pattern API: Set pattern {pattern_id} multipliers to 1.0")
        
        patterns_data = {}
        
        # Get all patterns (now with 1.0 multipliers)
        for pattern_id in wn.pattern_name_list:
            pattern = wn.get_pattern(pattern_id)
            patterns_data[pattern_id] = {
                "id": pattern_id,
                "multipliers": pattern.multipliers.tolist(),
                "description": f"Demand pattern {pattern_id} - 24 hours (neutralized for simulation)"
            }
        
        # Get node demands (fixed values)
        node_demands = {}
        for node_name in wn.node_name_list:
            node = wn.get_node(node_name)
            if hasattr(node, 'demand_timeseries_list') and node.demand_timeseries_list:
                base_demand_m3s = node.demand_timeseries_list[0].base_value
                base_demand_lps = base_demand_m3s * 1000  # Convert to LPS
                node_demands[node_name] = {
                    "base_demand_lps": base_demand_lps,
                    "base_demand_m3s": base_demand_m3s,
                    "description": f"Fixed demand for node {node_name}"
                }
        
        return {
            "success": True,
            "message": "Demand patterns retrieved successfully",
            "data": {
                "patterns": patterns_data,
                "node_demands": node_demands,
                "note": "Patterns are for display only. Simulation uses fixed demand values."
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting demand patterns: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "data": {"patterns": {}, "node_demands": {}}
        }
