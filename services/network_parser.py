"""
Network Parser Service - Parse EPANET input file để lấy topology
"""
import os
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class NetworkNode:
    """Network node với tọa độ thật"""
    id: str
    x_coord: float
    y_coord: float
    elevation: float = 0.0
    demand: float = 0.0
    node_type: str = "junction"  # junction, reservoir, tank

@dataclass
class NetworkPipe:
    """Network pipe với thông tin kết nối"""
    id: str
    from_node: str
    to_node: str
    length: float
    diameter: float
    roughness: float = 140.0
    status: str = "OPEN"

class NetworkParser:
    """Parser cho EPANET input file"""
    
    def __init__(self, inp_file_path: str = "epanetVip1.inp"):
        self.inp_file_path = inp_file_path
        self.nodes: List[NetworkNode] = []
        self.pipes: List[NetworkPipe] = []
        self.parsed = False  # Thêm cờ để kiểm tra đã parse chưa
        
    def parse_file(self) -> Dict[str, Any]:
        """Parse toàn bộ file EPANET"""
        if self.parsed:
            logger.info("Returning cached network topology.")
            return {
                "success": True,
                "nodes": [self._node_to_dict(node) for node in self.nodes],
                "pipes": [self._pipe_to_dict(pipe) for pipe in self.pipes],
                "total_nodes": len(self.nodes),
                "total_pipes": len(self.pipes)
            }
        
        logger.info(f"Parsing EPANET file: {self.inp_file_path}")
        try:
            if not os.path.exists(self.inp_file_path):
                raise FileNotFoundError(f"File {self.inp_file_path} không tồn tại")
            
            with open(self.inp_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse coordinates
            self._parse_coordinates(content)
            
            # Parse pipes
            self._parse_pipes(content)
            
            # Parse junctions để lấy elevation và demand
            self._parse_junctions(content)
            
            self.parsed = True
            logger.info(f"Finished parsing. Found {len(self.nodes)} nodes and {len(self.pipes)} pipes.")
            
            return {
                "success": True,
                "nodes": [self._node_to_dict(node) for node in self.nodes],
                "pipes": [self._pipe_to_dict(pipe) for pipe in self.pipes],
                "total_nodes": len(self.nodes),
                "total_pipes": len(self.pipes)
            }
            
        except Exception as e:
            logger.error(f"Error parsing EPANET file: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "nodes": [],
                "pipes": []
            }
    
    def _parse_coordinates(self, content: str):
        """Parse phần [COORDINATES]"""
        try:
            # Tìm phần [COORDINATES]
            coords_match = re.search(r'\[COORDINATES\](.*?)(?=\[|\Z)', content, re.DOTALL)
            if not coords_match:
                logger.warning("Không tìm thấy phần [COORDINATES]")
                return
            
            coords_section = coords_match.group(1)
            lines = coords_section.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Parse format: Node_ID X-Coord Y-Coord
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        node_id = parts[0]
                        x_coord = float(parts[1])
                        y_coord = float(parts[2])
                        
                        # Tạo node mới
                        node = NetworkNode(
                            id=node_id,
                            x_coord=x_coord,
                            y_coord=y_coord
                        )
                        self.nodes.append(node)
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Không thể parse line: {line} - {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error parsing coordinates: {str(e)}")
    
    def _parse_pipes(self, content: str):
        """Parse phần [PIPES]"""
        try:
            # Tìm phần [PIPES]
            pipes_match = re.search(r'\[PIPES\](.*?)(?=\[|\Z)', content, re.DOTALL)
            if not pipes_match:
                logger.warning("Không tìm thấy phần [PIPES]")
                return
            
            pipes_section = pipes_match.group(1)
            lines = pipes_section.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Parse format: Pipe_ID Node1 Node2 Length Diameter Roughness MinorLoss Status
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        pipe_id = parts[0]
                        from_node = parts[1]
                        to_node = parts[2]
                        length = float(parts[3])
                        diameter = float(parts[4])
                        roughness = float(parts[5])
                        minor_loss = float(parts[6])
                        status = parts[7]
                        
                        # Tạo pipe mới
                        pipe = NetworkPipe(
                            id=pipe_id,
                            from_node=from_node,
                            to_node=to_node,
                            length=length,
                            diameter=diameter,
                            roughness=roughness,
                            status=status
                        )
                        self.pipes.append(pipe)
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Không thể parse pipe line: {line} - {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error parsing pipes: {str(e)}")
    
    def _parse_junctions(self, content: str):
        """Parse phần [JUNCTIONS] để lấy elevation và demand"""
        try:
            # Tìm phần [JUNCTIONS]
            junctions_match = re.search(r'\[JUNCTIONS\](.*?)(?=\[|\Z)', content, re.DOTALL)
            if not junctions_match:
                logger.warning("Không tìm thấy phần [JUNCTIONS]")
                return
            
            junctions_section = junctions_match.group(1)
            lines = junctions_section.strip().split('\n')
            
            # Tạo dict để lookup junction data
            junction_data = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Parse format: Node_ID Elevation Demand Pattern
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        node_id = parts[0]
                        elevation = float(parts[1])
                        demand = float(parts[2])
                        
                        junction_data[node_id] = {
                            'elevation': elevation,
                            'demand': demand
                        }
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Không thể parse junction line: {line} - {e}")
                        continue
            
            # Cập nhật nodes với junction data
            for node in self.nodes:
                if node.id in junction_data:
                    node.elevation = junction_data[node.id]['elevation']
                    node.demand = junction_data[node.id]['demand']
                    node.node_type = "junction"
                        
        except Exception as e:
            logger.error(f"Error parsing junctions: {str(e)}")
    
    def _node_to_dict(self, node: NetworkNode) -> Dict[str, Any]:
        """Convert NetworkNode to dict"""
        return {
            "id": node.id,
            "x_coord": node.x_coord,
            "y_coord": node.y_coord,
            "elevation": node.elevation,
            "demand": node.demand,
            "node_type": node.node_type
        }
    
    def _pipe_to_dict(self, pipe: NetworkPipe) -> Dict[str, Any]:
        """Convert NetworkPipe to dict"""
        return {
            "id": pipe.id,
            "from_node": pipe.from_node,
            "to_node": pipe.to_node,
            "length": pipe.length,
            "diameter": pipe.diameter,
            "roughness": pipe.roughness,
            "status": pipe.status
        }

    def get_graph_structure(self) -> Dict[str, Any]:
        """Export graph structure cho Cytoscape.js visualization
        
        Returns:
            {
                nodes: [{id, label, type, demand, elevation}, ...],
                edges: [{id, source, target, length, diameter, flow, status}, ...]
            }
        """
        if not self.parsed:
            self.parse_file()

        # Convert nodes to Cytoscape format
        cytoscape_nodes = []
        for node in self.nodes:
            cytoscape_nodes.append({
                "data": {
                    "id": node.id,
                    "label": f"Node {node.id}",
                    "type": node.node_type,
                    "demand": node.demand,
                    "elevation": node.elevation,
                    "pressure": 0,  # Will be updated by simulation
                    "head": 0
                }
            })

        # Convert pipes to Cytoscape format (edges)
        cytoscape_edges = []
        for pipe in self.pipes:
            cytoscape_edges.append({
                "data": {
                    "id": pipe.id,
                    "source": pipe.from_node,
                    "target": pipe.to_node,
                    "label": pipe.id,
                    "length": pipe.length,
                    "diameter": pipe.diameter,
                    "roughness": pipe.roughness,
                    "status": pipe.status,
                    "flow": 0,  # Will be updated by simulation
                    "velocity": 0,
                    "headloss": 0
                }
            })

        logger.info(f"Graph structure: {len(cytoscape_nodes)} nodes, {len(cytoscape_edges)} edges")

        return {
            "success": True,
            "nodes": cytoscape_nodes,
            "edges": cytoscape_edges,
            "total_nodes": len(cytoscape_nodes),
            "total_edges": len(cytoscape_edges)
        }

# Global parser instance
network_parser = NetworkParser()
