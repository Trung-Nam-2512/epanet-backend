import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from utils.logger import logger

class SCADAService:
    """Service de ket noi voi API SCADA cua Nuoc Ngam Sai Gon"""
    
    def __init__(self):
        # Load config from file
        self._load_config()
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _load_config(self):
        """Load configuration from scada_mapping.json"""
        try:
            with open("config/scada_mapping.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Load API config
            api_config = config.get("api_config", {})
            self.base_url = api_config.get("base_url", "https://scada.nuocngamsaigon.com/scada-api/api/station")
            self.token = api_config.get("token", "")
            
            # Load SCADA stations (KHONG co mapping voi EPANET nodes)
            scada_stations_config = config.get("scada_stations", {})
            self.scada_stations = {}
            for station_code, station_info in scada_stations_config.items():
                self.scada_stations[station_code] = {
                    "description": station_info.get("description", ""),
                    "location": station_info.get("location", ""),
                    "data_types": station_info.get("data_types", []),
                    "note": station_info.get("note", "")
                }
            
            logger.info(f"Loaded {len(self.scada_stations)} SCADA stations - boundary conditions only")
            
        except Exception as e:
            logger.error(f"Error loading SCADA config: {str(e)}")
            # Fallback to default config
            self.base_url = "https://scada.nuocngamsaigon.com/scada-api/api/station"
            self.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1bmlxdWVfbmFtZSI6Im5uc2ciLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3VzZXJkYXRhIjoiVDM4WTNqVFJ4Z1JtNFNNOFBoY2dxQT09IiwibmJmIjoxNzYwNTI1MzE1LCJleHAiOjE3NjMyMDM3MTUsImlhdCI6MTc2MDUyNTMxNX0.ddpgC_L7C6shfUYYor3Gmf6RJO9v-C0yfj7r5QXW7rk"
            self.scada_stations = {}
    
    def get_station_data_by_hour(self, station_code: str, from_date: str, to_date: str) -> Dict[str, Any]:
        """
        Lay du lieu tram theo gio tu API SCADA
        
        Args:
            station_code: Ma tram (vi du: "13085")
            from_date: Ngay bat dau (format: "2025-10-22 00:00")
            to_date: Ngay ket thuc (format: "2025-10-24 00:00")
        
        Returns:
            Dict chua du lieu tu API SCADA
        """
        try:
            url = f"{self.base_url}/GetStationDataByHour"
            payload = {
                "stationCode": station_code,
                "fromDate": from_date,
                "toDate": to_date
            }
            
            logger.info(f"Getting SCADA data for station {station_code} from {from_date} to {to_date}")
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"SCADA data retrieved successfully for station {station_code}")
                return {
                    "success": True,
                    "data": data,
                    "station_code": station_code,
                    "from_date": from_date,
                    "to_date": to_date
                }
            else:
                logger.error(f"SCADA API Error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "message": response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error(f" Timeout khi goi API SCADA cho tram {station_code}")
            return {
                "success": False,
                "error": "Timeout",
                "message": "API SCADA khong phan hoi trong thoi gian cho phep"
            }
        except Exception as e:
            logger.error(f"Error calling SCADA API: {str(e)}")
            return {
                "success": False,
                "error": "Exception",
                "message": str(e)
            }
    
    def get_multiple_stations_data(self, station_codes: List[str], from_date: str, to_date: str) -> Dict[str, Any]:
        """
        Lay du lieu tu nhieu tram cung luc
        
        Args:
            station_codes: Danh sach ma tram
            from_date: Ngay bat dau
            to_date: Ngay ket thuc
        
        Returns:
            Dict chua du lieu tu tat ca tram
        """
        results = {}
        successful_stations = 0
        failed_stations = 0
        
        logger.info(f"Getting data from {len(station_codes)} stations")
        
        for station_code in station_codes:
            result = self.get_station_data_by_hour(station_code, from_date, to_date)
            results[station_code] = result
            
            if result["success"]:
                successful_stations += 1
            else:
                failed_stations += 1
        
        logger.info(f"Completed: {successful_stations} successful, {failed_stations} failed")
        
        return {
            "success": successful_stations > 0,
            "results": results,
            "summary": {
                "total_stations": len(station_codes),
                "successful": successful_stations,
                "failed": failed_stations
            }
        }
    
    def parse_scada_data(self, scada_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse du lieu SCADA thanh dinh dang phu hop cho EPANET
        
        Args:
            scada_data: Du lieu tho tu API SCADA
        
        Returns:
            List cac dict chua du lieu da parse
        """
        parsed_data = []
        
        try:
            # Debug: Log cấu trúc dữ liệu SCADA
            logger.info(f"SCADA data keys: {list(scada_data.keys())}")
            logger.info(f"SCADA data type: {type(scada_data)}")
            
            # Xu ly cau truc du lieu SCADA thuc te
            # Dữ liệu thực tế có cấu trúc: {"code": 200, "message": "success", "data": [...]}
            if "data" in scada_data and isinstance(scada_data["data"], list):
                logger.info(f"Found data array with {len(scada_data['data'])} items")
                # Nhom du lieu theo thoi gian
                time_groups = {}
                
                for item in scada_data["data"]:
                    timestamp = item.get("transferTime", "")
                    if timestamp not in time_groups:
                        time_groups[timestamp] = {}
                    
                    # Luu du lieu theo parameterCode
                    param_code = item.get("parameterCode", "")
                    time_groups[timestamp][param_code] = {
                        "value": item.get("value", 0),
                        "unit": item.get("unitCode", ""),
                        "name": item.get("parameterName", ""),
                        "station_code": item.get("stationCode", "")
                    }
                
                # Chuyen doi thanh format chuan
                for timestamp, params in time_groups.items():
                    # Lấy station_code từ item đầu tiên
                    station_code = ""
                    for param_data in params.values():
                        if "station_code" in param_data:
                            station_code = param_data["station_code"]
                            break
                    
                    parsed_item = {
                        "timestamp": timestamp,
                        "pressure": self._extract_pressure_from_params(params),
                        "flow": self._extract_flow_from_params(params),
                        "voltage": self._extract_voltage_from_params(params),
                        "station_code": station_code
                    }
                    parsed_data.append(parsed_item)
            
            logger.info(f"Parsed {len(parsed_data)} SCADA data records")
            
        except Exception as e:
            logger.error(f"Error parsing SCADA data: {str(e)}")
            logger.error(f"SCADA data structure: {scada_data}")
        
        return parsed_data
    
    def _extract_pressure_from_params(self, params: Dict[str, Any]) -> Optional[float]:
        """Trich xuat ap luc tu parameters SCADA"""
        # P1 = Ap luc vao
        if "P1" in params:
            try:
                return float(params["P1"]["value"])
            except (ValueError, TypeError, KeyError):
                pass
        return None
    
    def _extract_flow_from_params(self, params: Dict[str, Any]) -> Optional[float]:
        """Trich xuat luu luong tu parameters SCADA"""
        # Q1 = Luu luong thuan, Q2 = Luu luong nghich
        flow_forward = 0
        flow_reverse = 0
        
        if "Q1" in params:
            try:
                flow_forward = float(params["Q1"]["value"])
                # Convert từ L/s sang LPS (Liters Per Second)
                # Dữ liệu SCADA đã là L/s nên không cần convert
            except (ValueError, TypeError, KeyError):
                pass
        
        if "Q2" in params:
            try:
                flow_reverse = float(params["Q2"]["value"])
            except (ValueError, TypeError, KeyError):
                pass
        
        # Luu luong thuc = thuan - nghich (L/s)
        net_flow = flow_forward - flow_reverse
        return net_flow if net_flow != 0 else None
    
    def _extract_voltage_from_params(self, params: Dict[str, Any]) -> Optional[float]:
        """Trich xuat dien ap tu parameters SCADA"""
        # V = Nguon (dien ap)
        if "V" in params:
            try:
                return float(params["V"]["value"])
            except (ValueError, TypeError, KeyError):
                pass
        return None
    
    def _extract_pressure(self, data_item: Dict[str, Any]) -> Optional[float]:
        """Trich xuat ap luc tu du lieu SCADA (legacy method)"""
        # Cac truong co the chua ap luc
        pressure_fields = ["pressure", "Pressure", "PRESSURE", "ap_luc", "apLuc"]
        
        for field in pressure_fields:
            if field in data_item and data_item[field] is not None:
                try:
                    return float(data_item[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_flow(self, data_item: Dict[str, Any]) -> Optional[float]:
        """Trich xuat luu luong tu du lieu SCADA (legacy method)"""
        # Cac truong co the chua luu luong
        flow_fields = ["flow", "Flow", "FLOW", "luu_luong", "luuLuong", "flowRate"]
        
        for field in flow_fields:
            if field in data_item and data_item[field] is not None:
                try:
                    return float(data_item[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_level(self, data_item: Dict[str, Any]) -> Optional[float]:
        """Trich xuat muc nuoc tu du lieu SCADA (legacy method)"""
        level_fields = ["level", "Level", "LEVEL", "muc_nuoc", "mucNuoc", "waterLevel"]
        
        for field in level_fields:
            if field in data_item and data_item[field] is not None:
                try:
                    return float(data_item[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_quality(self, data_item: Dict[str, Any]) -> Optional[float]:
        """Trich xuat chat luong nuoc tu du lieu SCADA (legacy method)"""
        quality_fields = ["quality", "Quality", "QUALITY", "chat_luong", "chatLuong", "turbidity", "pH"]
        
        for field in quality_fields:
            if field in data_item and data_item[field] is not None:
                try:
                    return float(data_item[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def convert_to_epanet_format(self, scada_data: List[Dict[str, Any]], station_code: str) -> List[Dict[str, Any]]:
        """
        Chuyen doi du lieu SCADA thanh dinh dang EPANET - CHI SU DUNG LAM BOUNDARY CONDITION
        
        Args:
            scada_data: Du lieu da parse tu SCADA
            station_code: Ma tram SCADA
        
        Returns:
            List du lieu theo dinh dang EPANET (chi lam boundary condition)
        """
        epanet_data = []
        
        for item in scada_data:
            # SCADA chi cung cap data tu dong ho bom tong
            pressure = item.get("pressure")
            flow = item.get("flow")
            
            # SCADA data chi la boundary condition, KHONG map voi node cu the
            epanet_item = {
                "station_code": station_code,
                "timestamp": item.get("timestamp"),
                "pressure": pressure,  # Ap luc tu dong ho bom tong
                "flow": flow,          # Luu luong tu dong ho bom tong
                "description": f"SCADA data from station {station_code} - boundary condition only"
            }
            epanet_data.append(epanet_item)
        
        logger.info(f"Converting {len(epanet_data)} SCADA records from station {station_code} - boundary condition only")
        return epanet_data
    
    def _calculate_demand(self, data_item: Dict[str, Any]) -> Optional[float]:
        """Lay nhu cau nuoc tu file .inp (khong tinh toan tu SCADA)"""
        # Demand da co san trong file .inp, khong can tinh tu SCADA
        # Chi can lay tu file .inp cho nut tuong ung
        return None  # Se su dung demand tu file .inp
    
    def _calculate_head(self, data_item: Dict[str, Any]) -> Optional[float]:
        """Tinh toan cot ap tu du lieu SCADA"""
        pressure = data_item.get("pressure")
        level = data_item.get("level")
        
        if pressure is not None:
            # Cot ap = ap luc + muc nuoc (neu co)
            head = pressure
            if level is not None:
                head += level
            return head
        
        return None
    
    def get_realtime_data_for_epanet(self, station_codes: List[str], hours_back: int = 24) -> Dict[str, Any]:
        """
        Lay du lieu thoi gian thuc cho mo phong EPANET - CHI LAM BOUNDARY CONDITION
        
        Args:
            station_codes: Danh sach ma tram SCADA
            hours_back: So gio lui lai tu hien tai
        
        Returns:
            Du lieu SCADA chi lam boundary condition cho EPANET simulation
        """
        # Tinh toan thoi gian - lam tron theo step 1h
        now = datetime.now()
        # Lam tron xuong gio gan nhat (5h05 -> 5h00)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        from_date = (current_hour - timedelta(hours=hours_back)).strftime("%Y-%m-%d %H:%M")
        to_date = current_hour.strftime("%Y-%m-%d %H:%M")
        
        logger.info(f"Getting SCADA data from {from_date} to {to_date} - boundary condition only")
        
        # Lay du lieu tu tat ca tram SCADA
        scada_results = self.get_multiple_stations_data(station_codes, from_date, to_date)
        
        # Xu ly va chuyen doi du lieu - CHI LAM BOUNDARY CONDITION
        boundary_conditions = {}
        
        for station_code, result in scada_results["results"].items():
            if result["success"]:
                # Parse du lieu SCADA
                parsed_data = self.parse_scada_data(result["data"])
                
                # Chuyen doi sang dinh dang EPANET - CHI LAM BOUNDARY CONDITION
                boundary_data = self.convert_to_epanet_format(parsed_data, station_code)
                
                if boundary_data:
                    boundary_conditions[station_code] = boundary_data
        
        return {
            "success": len(boundary_conditions) > 0,
            "boundary_conditions": boundary_conditions,
            "summary": {
                "stations_processed": len(boundary_conditions),
                "total_records": sum(len(data) for data in boundary_conditions.values()),
                "note": "SCADA data used only as boundary conditions for EPANET simulation"
            }
        }

# Global service instance
scada_service = SCADAService()
