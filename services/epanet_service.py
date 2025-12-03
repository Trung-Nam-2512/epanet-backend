import os
import tempfile
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

try:
    import wntr
    print("WNTR library loaded successfully")
    epanet = wntr
except ImportError:
    try:
        from epanet import toolkit as epanet
        print("EPANET toolkit loaded successfully")
    except ImportError:
        print("EPANET toolkit not available. Using mock implementation.")
        epanet = None

from core.config import settings
from core.database import db_manager
from models.schemas import SimulationInput, SimulationResult, SimulationStatus, NodeData
from utils.logger import logger
from services.scada_boundary_service import scada_boundary_service

class EPANETService:
    def __init__(self):
        self.input_file = settings.epanet_input_file
        self.temp_dir = tempfile.mkdtemp()
        
    def run_simulation(
        self, 
        simulation_input: SimulationInput,
        scada_boundary_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> SimulationResult:
        """
        Chay mo phong EPANET voi du lieu dau vao
        
        Args:
            simulation_input: Input parameters cho simulation
            scada_boundary_data: Optional SCADA boundary conditions dict (key: station_code, value: list of records)
        """
        # Convert to dict with proper serialization
        input_dict = simulation_input.dict()
        # Convert NodeData objects to dicts
        if 'real_time_data' in input_dict and input_dict['real_time_data']:
            if 'nodes' in input_dict['real_time_data']:
                input_dict['real_time_data']['nodes'] = [
                    node.dict() if hasattr(node, 'dict') else node 
                    for node in input_dict['real_time_data']['nodes']
                ]
        
        run_id = db_manager.save_simulation_run("running", input_dict)
        
        try:
            # Always try real EPANET simulation first
            return self._real_simulation(simulation_input, run_id, scada_boundary_data)
            
        except Exception as e:
            error_msg = f"Simulation failed: {str(e)}"
            db_manager.save_simulation_run("failed", error_message=error_msg)
            return SimulationResult(
                run_id=run_id,
                status=SimulationStatus.FAILED,
                timestamp=datetime.now(),
                duration=0,
                nodes_results={},
                pipes_results={},
                pumps_results={},
                error_message=error_msg
            )
    
    def _real_simulation(
        self, 
        simulation_input: SimulationInput, 
        run_id: int,
        scada_boundary_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> SimulationResult:
        """Chay mo phong EPANET thuc te voi WNTR"""
        try:
            # Import WNTR
            import wntr
            
            # Load water network model
            wn = wntr.network.WaterNetworkModel(self.input_file)
            
            # ✅ DEBUG: Log initial reservoir head BEFORE SCADA application
            logger.info(f"[DEBUG] All patterns in network: {list(wn.pattern_name_list)}")
            for reservoir_name in wn.reservoir_name_list:
                reservoir = wn.get_node(reservoir_name)
                logger.info(f"[DEBUG] Initial reservoir {reservoir_name} base_head: {reservoir.base_head:.2f}m, pattern: {reservoir.head_pattern_name}")
                if hasattr(reservoir, 'elevation'):
                    logger.info(f"[DEBUG] Initial reservoir {reservoir_name} elevation: {reservoir.elevation:.2f}m")
                # Check head_timeseries
                if hasattr(reservoir, 'head_timeseries'):
                    test_head = reservoir.head_timeseries.at(0)
                    logger.info(f"[DEBUG] Initial reservoir {reservoir_name} head_timeseries.at(0): {test_head:.2f}m")
            
            # Set simulation options
            wn.options.time.duration = simulation_input.duration * 3600  # Convert to seconds
            wn.options.time.hydraulic_timestep = simulation_input.hydraulic_timestep * 3600
            wn.options.time.report_timestep = simulation_input.report_timestep * 3600
            
            # ✅ DEMAND LOGIC: Sử dụng demand cố định từ file .inp (không áp dụng pattern)
            # Pattern chỉ là hệ số tham khảo cho user, không dùng trong simulation
            wn.options.time.start_clocktime = 0  # Start from beginning
            wn.options.time.pattern_start = 0    # Pattern starts from beginning (but not used)
            
            # ✅ BEST SOLUTION: Set all EXISTING pattern multipliers to 1.0 (for demand patterns only)
            # This keeps pattern structure intact but neutralizes its effect
            # NOTE: SCADA head patterns will be created AFTER this, so they won't be affected
            existing_patterns = list(wn.pattern_name_list)  # Copy list to avoid modification during iteration
            for pattern_id in existing_patterns:
                # Skip SCADA head patterns (they will be created later)
                if pattern_id.startswith("SCADA_HEAD_"):
                    continue
                pattern = wn.get_pattern(pattern_id)
                pattern.multipliers = [1.0] * len(pattern.multipliers)
                logger.info(f"Set pattern {pattern_id} multipliers to 1.0 (neutral effect)")
            
            logger.info("Applied fixed demand logic - pattern multipliers set to 1.0")
            
            # ✅ APPLY SCADA BOUNDARY CONDITIONS (nếu có)
            if scada_boundary_data:
                logger.info("Applying SCADA boundary conditions to WNTR model...")
                # Extract simulation_start_time từ SCADA data nếu có
                simulation_start_time = None
                for station_code, records in scada_boundary_data.items():
                    if records:
                        first_record = records[0]
                        timestamp_str = first_record.get('timestamp')
                        if timestamp_str:
                            try:
                                from datetime import datetime
                                if 'T' in timestamp_str:
                                    simulation_start_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                else:
                                    simulation_start_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
                                break
                            except:
                                pass
                
                scada_applied = scada_boundary_service.apply_scada_boundary_conditions(
                    wn=wn,
                    scada_boundary_data=scada_boundary_data,
                    simulation_duration_hours=simulation_input.duration,
                    hydraulic_timestep_hours=simulation_input.hydraulic_timestep,
                    simulation_start_time=simulation_start_time  # Fix: Pass simulation_start_time
                )
                if scada_applied:
                    logger.info("[OK] SCADA boundary conditions applied successfully")
                    # ✅ DEBUG: Log reservoir head AFTER SCADA application
                    for reservoir_name in wn.reservoir_name_list:
                        reservoir = wn.get_node(reservoir_name)
                        logger.info(f"[DEBUG] After SCADA - reservoir {reservoir_name} base_head: {reservoir.base_head:.2f}m, pattern: {reservoir.head_pattern_name}")
                        if reservoir.head_pattern_name:
                            pattern = wn.get_pattern(reservoir.head_pattern_name)
                            logger.info(f"[DEBUG] Pattern {reservoir.head_pattern_name} multipliers: {pattern.multipliers[:5]}... (first 5)")
                else:
                    logger.warning("[WARN] SCADA boundary conditions not applied - using INP file boundary conditions")
            else:
                logger.info("No SCADA boundary data provided - using INP file boundary conditions")
            
            # Legacy: Update real-time data if available (for backward compatibility)
            # Note: This is now secondary to SCADA boundary conditions
            if simulation_input.real_time_data:
                self._update_wntr_real_time_data(wn, simulation_input.real_time_data.nodes)
            
            # Run simulation
            sim = wntr.sim.WNTRSimulator(wn)
            results = sim.run_sim()
            
            # Extract results
            try:
                processed_results = self._extract_wntr_results(results, wn)
                logger.info(f"Processed results keys: {list(processed_results.keys())}")
                logger.info(f"Nodes in processed results: {len(processed_results.get('nodes', {}))}")
            except Exception as e:
                logger.error(f"Error in _extract_wntr_results: {str(e)}")
                processed_results = {"nodes": {}, "pipes": {}, "pumps": {}}
            
            # Save results to database
            db_manager.save_simulation_run("completed", results=processed_results)
            
            return SimulationResult(
                run_id=run_id,
                status=SimulationStatus.COMPLETED,
                timestamp=datetime.now(),
                duration=simulation_input.duration,
                nodes_results=processed_results.get("nodes", {}),
                pipes_results=processed_results.get("pipes", {}),
                pumps_results=processed_results.get("pumps", {}),
            )
            
        except Exception as e:
            logger.error(f"Error running EPANET simulation: {str(e)}")
            # Return error instead of mock
            return SimulationResult(
                run_id=run_id,
                status=SimulationStatus.FAILED,
                timestamp=datetime.now(),
                duration=0,
                nodes_results={},
                pipes_results={},
                pumps_results={},
                error_message=f"EPANET simulation failed: {str(e)}"
            )
    
    
    
    def _update_wntr_real_time_data(self, wn, real_time_data: List[NodeData]):
        """Cap nhat du lieu thoi gian thuc cho WNTR - CHI SU DUNG LAM BOUNDARY CONDITION"""
        try:
            # SCADA data chi la boundary condition, KHONG cap nhat cho cac node cu the
            logger.info("SCADA data used only as boundary condition - no node updates needed")
            
            # Log thong tin SCADA de tham khao
            for data in real_time_data:
                if hasattr(data, 'pressure') and data.pressure is not None:
                    logger.info(f"SCADA pressure: {data.pressure} m (boundary condition only)")
                if hasattr(data, 'flow') and data.flow is not None:
                    logger.info(f"SCADA flow: {data.flow} L/s (boundary condition only)")
                        
        except Exception as e:
            logger.error(f"Error processing SCADA boundary conditions: {str(e)}")
    
    def _extract_wntr_results(self, results, wn) -> Dict[str, Any]:
        """Trich xuat ket qua tu WNTR"""
        try:
            nodes_results = {}
            pipes_results = {}
            pumps_results = {}
            
            # Lay ket qua nodes tu WNTR
            if hasattr(results, 'node'):
                logger.info(f"Processing {len(wn.node_name_list)} nodes from WNTR")
                processed_count = 0
                
                # ✅ DEBUG: Check pumps BEFORE processing nodes
                logger.info(f"[DEBUG] Total pumps in network: {len(wn.pump_name_list)}")
                logger.info(f"[DEBUG] Pump names: {list(wn.pump_name_list)}")
                
                # ✅ DEBUG: Check reservoir head in simulation results
                for reservoir_name in wn.reservoir_name_list:
                    if reservoir_name in results.node['head'].columns:
                        reservoir_heads = results.node['head'].loc[:, reservoir_name]
                        logger.info(f"[DEBUG] Reservoir {reservoir_name} head in simulation results:")
                        for i, (time, head) in enumerate(reservoir_heads.items()):
                            if i < 3:  # Log first 3 time steps
                                logger.info(f"  Time {time}s: {head:.2f}m")
                
                # ✅ DEBUG: Check pump head gain and node 306 head
                if len(wn.pump_name_list) == 0:
                    logger.warning("[DEBUG] ⚠️ NO PUMPS FOUND IN NETWORK!")
                for pump_name in wn.pump_name_list:
                    pump = wn.get_link(pump_name)
                    logger.info(f"[DEBUG] Pump {pump_name}: {pump.start_node_name} → {pump.end_node_name}")
                    logger.info(f"  Pump type: {pump.pump_type if hasattr(pump, 'pump_type') else 'N/A'}")
                    logger.info(f"  Initial status: {pump.initial_status}")
                    if hasattr(pump, 'head_curve_name'):
                        logger.info(f"  Head curve: {pump.head_curve_name}")
                        try:
                            curve = wn.get_curve(pump.head_curve_name)
                            if hasattr(curve, 'points'):
                                logger.info(f"  Head curve points: {curve.points[:5] if len(curve.points) > 5 else curve.points}")
                        except:
                            pass
                    if pump.start_node_name in results.node['head'].columns and pump.end_node_name in results.node['head'].columns:
                        start_head = results.node['head'].loc[results.node['head'].index[0], pump.start_node_name]
                        end_head = results.node['head'].loc[results.node['head'].index[0], pump.end_node_name]
                        head_gain = end_head - start_head
                        logger.info(f"  Start node ({pump.start_node_name}) head: {start_head:.2f}m")
                        logger.info(f"  End node ({pump.end_node_name}) head: {end_head:.2f}m")
                        logger.info(f"  Head gain: {head_gain:.2f}m")
                        # Check pump status and flow
                        if hasattr(results, 'link'):
                            if 'status' in results.link and pump_name in results.link['status'].columns:
                                pump_status = results.link['status'].loc[results.link['status'].index[0], pump_name]
                                logger.info(f"  Pump status: {pump_status} (1=Open, 0=Closed)")
                            if 'flowrate' in results.link and pump_name in results.link['flowrate'].columns:
                                pump_flow = results.link['flowrate'].loc[results.link['flowrate'].index[0], pump_name]
                                pump_flow_lps = pump_flow * 1000
                                logger.info(f"  Pump flow: {pump_flow:.4f} m³/s ({pump_flow_lps:.2f} LPS)")
                                # Check if pump should be running based on head curve
                                if hasattr(pump, 'head_curve_name'):
                                    try:
                                        curve = wn.get_curve(pump.head_curve_name)
                                        if hasattr(curve, 'points') and len(curve.points) > 0:
                                            # Get head gain from curve at current flow
                                            # Curve format: (flow, head_gain)
                                            max_head_gain = max([p[1] for p in curve.points])
                                            logger.info(f"  Max head gain from curve: {max_head_gain:.2f}m")
                                            if head_gain > max_head_gain + 0.1:
                                                logger.warning(f"  ⚠️ WARNING: Head gain ({head_gain:.2f}m) > Max curve head ({max_head_gain:.2f}m) - Pump should be CLOSED!")
                                    except:
                                        pass
                
                for node_name in wn.node_name_list:
                    try:
                        node_data = []
                        logger.info(f"Processing node: {node_name}")
                        for i, time in enumerate(results.node['pressure'].index):
                            pressure = results.node['pressure'].loc[time, node_name]
                            head = results.node['head'].loc[time, node_name]
                            demand = results.node['demand'].loc[time, node_name]
                            
                            # Debug: Check WNTR units (only for first node, first time step)
                            if node_name == "2" and i == 0:
                                node_obj = wn.get_node(node_name)
                                logger.info(f"[DEBUG] Node {node_name} details:")
                                logger.info(f"  Elevation: {node_obj.elevation:.2f}m")
                                logger.info(f"  Head: {head:.2f}m")
                                logger.info(f"  Pressure: {pressure:.2f}m")
                                logger.info(f"  Demand: {demand} (type: {type(demand)})")
                                # Check if node is connected to reservoir or pump end node
                                connected_links = wn.get_links_for_node(node_name)
                                logger.info(f"  Connected links: {list(connected_links)}")
                                for link_name in connected_links:
                                    link = wn.get_link(link_name)
                                    link_type = type(link).__name__
                                    logger.info(f"  Link {link_name}: type={link_type}")
                                    if hasattr(link, 'start_node_name'):
                                        logger.info(f"    Start node: {link.start_node_name}, End node: {link.end_node_name}")
                                        # Check if connected to TXU2
                                        if link.start_node_name == 'TXU2' or link.end_node_name == 'TXU2':
                                            logger.info(f"    ✅ Connected to TXU2 via {link_name} (type: {link_type})")
                                        # Check if connected to node 306 (pump end node)
                                        if link.start_node_name == '306' or link.end_node_name == '306':
                                            logger.info(f"    ✅ Connected to node 306 (pump end) via {link_name} (type: {link_type})")
                                            # Check head of node 306
                                            if '306' in results.node['head'].columns:
                                                node306_head = results.node['head'].loc[results.node['head'].index[0], '306']
                                                logger.info(f"    Node 306 head: {node306_head:.2f}m")
                                        if link_type == 'Pump':
                                            if hasattr(link, 'head_curve_name'):
                                                logger.info(f"    Pump head curve: {link.head_curve_name}")
                                                # Get head curve
                                                try:
                                                    curve = wn.get_curve(link.head_curve_name)
                                                    logger.info(f"    Head curve points: {curve.points[:3] if hasattr(curve, 'points') else 'N/A'}")
                                                except:
                                                    pass
                                if len(results.link['flowrate']) > 0:
                                    logger.info(f"  WNTR flowrate sample: {results.link['flowrate'].iloc[0, 0]}")
                            
                            # Convert m³/s to LPS: multiply by 1000
                            # EPANET convention:
                            # - Positive demand = consumption (water flowing INTO node) → flow should be POSITIVE
                            # - Negative demand = supply (water flowing OUT OF node) → flow should be NEGATIVE
                            if demand is not None and demand != 0:
                                demand_lps = demand * 1000  # Convert m³/s to LPS
                                flow = demand_lps  # Flow = demand (keep same sign: positive for consumption, negative for supply)
                            else:
                                demand_lps = 0.0
                                flow = 0.0
                            
                            node_data.append({
                                "node_id": node_name,
                                "pressure": float(pressure) if pressure is not None else 0.0,
                                "head": float(head) if head is not None else 0.0,
                                "demand": float(demand_lps),
                                "flow": float(flow)
                            })
                        nodes_results[node_name] = node_data
                        processed_count += 1
                        if node_name == "2":  # Debug first node
                            logger.info(f"Node 2 data: {len(node_data)} records")
                    except Exception as e:
                        logger.warning(f"Error processing node {node_name}: {str(e)}")
                        continue
                
                logger.info(f"Successfully processed {processed_count}/{len(wn.node_name_list)} nodes")
            
            # Lay ket qua pipes
            if hasattr(results, 'link'):
                for pipe_name in wn.pipe_name_list:
                    pipe_data = []
                    
                    for i, time in enumerate(results.link['flowrate'].index):
                        flow = results.link['flowrate'].loc[time, pipe_name]
                        
                        # Convert m³/s to LPS: multiply by 1000
                        flow_lps = flow * 1000  # Convert m³/s to LPS
                        
                        pipe_data.append({
                            "timestamp": time,
                            "flow": flow_lps
                        })
                    pipes_results[pipe_name] = pipe_data
            
            # Lay ket qua pumps
            if hasattr(results, 'link'):
                for pump_name in wn.pump_name_list:
                    pump_data = []
                    for i, time in enumerate(results.link['flowrate'].index):
                        flow = results.link['flowrate'].loc[time, pump_name]
                        flow_lps = flow * 1000  # Convert m³/s to LPS
                        
                        pump_data.append({
                            "timestamp": time,
                            "flow": flow_lps,
                            "head": 0.0,  # Simplified for now
                            "power": 0.0  # Simplified for now
                        })
                    pumps_results[pump_name] = pump_data
            
            # Debug: Log results count
            logger.info(f"Extracted results - Nodes: {len(nodes_results)}, Pipes: {len(pipes_results)}, Pumps: {len(pumps_results)}")
            
            return {
                "nodes": nodes_results,
                "pipes": pipes_results,
                "pumps": pumps_results
            }
            
        except Exception as e:
            logger.error(f"Error extracting WNTR results: {str(e)}")
            return {"nodes": {}, "pipes": {}, "pumps": {}}
    
    def _create_updated_input_file(self, simulation_input: SimulationInput) -> str:
        """Tao file input EPANET voi du lieu cap nhat"""
        temp_file = os.path.join(self.temp_dir, "updated_input.inp")
        
        # Doc file goc
        with open(self.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cap nhat thoi gian mo phong
        content = self._update_simulation_time(content, simulation_input)
        
        # Cap nhat du lieu thoi gian thuc neu co
        if simulation_input.real_time_data:
            content = self._update_real_time_data_in_file(content, simulation_input.real_time_data)
        
        # Ghi file tam thoi
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return temp_file
    
    def _update_simulation_time(self, content: str, simulation_input: SimulationInput) -> str:
        """Cap nhat thoi gian mo phong trong file input"""
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('[TIMES]'):
                updated_lines.append(line)
                # Tim va cap nhat cac thong so thoi gian
                continue
            elif 'Duration' in line:
                updated_lines.append(f" Duration           {simulation_input.duration}:00")
            elif 'Hydraulic Timestep' in line:
                updated_lines.append(f" Hydraulic Timestep {simulation_input.hydraulic_timestep}:00")
            elif 'Report Timestep' in line:
                updated_lines.append(f" Report Timestep    {simulation_input.report_timestep}:00")
            else:
                updated_lines.append(line)
        
        return '\n'.join(updated_lines)
    
    def _update_real_time_data_in_file(self, content: str, real_time_data) -> str:
        """Cap nhat du lieu thoi gian thuc trong file input"""
        # Implementation de cap nhat demand va pressure tu du lieu thoi gian thuc
        # Day la phan phuc tap can xu ly theo logic nghiep vu cu the
        return content
    
    def _get_node_ids_from_input(self) -> List[str]:
        """Lay danh sach ID cac nut tu file input - tat ca unique nodes"""
        import re
        
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Lay tat ca unique node IDs tu JUNCTIONS, RESERVOIRS, TANKS
            junction_pattern = r'^ (\d+)\s+([\d.]+)\s+([\d.]+)'
            reservoir_pattern = r'^ (\d+)\s+([\d.]+)'
            tank_pattern = r'^ (\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'
            
            junctions = re.findall(junction_pattern, content, re.MULTILINE)
            reservoirs = re.findall(reservoir_pattern, content, re.MULTILINE)
            tanks = re.findall(tank_pattern, content, re.MULTILINE)
            
            # Lay unique node IDs
            junction_ids = set([j[0] for j in junctions])
            reservoir_ids = set([r[0] for r in reservoirs])
            tank_ids = set([t[0] for t in tanks])
            
            # Union tat ca unique nodes
            all_unique_nodes = junction_ids.union(reservoir_ids).union(tank_ids)
            node_ids = list(all_unique_nodes)
            
            print(f"Found {len(node_ids)} unique nodes: {len(junction_ids)} junctions, {len(reservoir_ids)} reservoirs, {len(tank_ids)} tanks")
            
        except Exception as e:
            print(f"Error reading node IDs: {e}")
            # Fallback - use the 205 unique nodes we found
            node_ids = ['2', '3', '31', '43', '64', '65', '80', '88', '93', '99', '914', '1280', '699', '1063', '16', '1018', '1299', '1437', '613', '1083']
        
        return node_ids
    
    def _extract_results(self, ph) -> Dict[str, Any]:
        """Trich xuat ket qua tu mo phong EPANET"""
        # Implementation de trich xuat ket qua tu EPANET
        # Bao gom: pressure, flow, head cho cac nut va duong ong
        return {}
    
    def get_network_info(self) -> Dict[str, Any]:
        """Lay thong tin ve mang luoi"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            info = {
                'total_nodes': 0,
                'total_pipes': 0,
                'total_pumps': 0,
                'total_reservoirs': 0
            }
            
            current_section = None
            
            for line in lines:
                if line.startswith('[JUNCTIONS]'):
                    current_section = 'junctions'
                    continue
                elif line.startswith('[PIPES]'):
                    current_section = 'pipes'
                    continue
                elif line.startswith('[PUMPS]'):
                    current_section = 'pumps'
                    continue
                elif line.startswith('[RESERVOIRS]'):
                    current_section = 'reservoirs'
                    continue
                elif line.startswith('[') and current_section:
                    current_section = None
                    continue
                elif current_section and line.strip() and not line.startswith(';'):
                    if current_section == 'junctions':
                        info['total_nodes'] += 1
                    elif current_section == 'pipes':
                        info['total_pipes'] += 1
                    elif current_section == 'pumps':
                        info['total_pumps'] += 1
                    elif current_section == 'reservoirs':
                        info['total_reservoirs'] += 1
            
            return info
            
        except Exception as e:
            print(f"Error reading network info: {e}")
            return {
                'total_nodes': 0,
                'total_pipes': 0,
                'total_pumps': 0,
                'total_reservoirs': 0
            }

# Global service instance
epanet_service = EPANETService()
