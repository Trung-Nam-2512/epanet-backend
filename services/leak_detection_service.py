"""
Service để phát hiện rò rỉ sử dụng model đã train
"""
import pickle
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from utils.logger import logger

class LeakDetectionService:
    """Service để detect leak từ simulation results"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_cols = None
        self.threshold = 0.5  # Default threshold (will be overridden by metadata if available)
        self.metadata = None
        self.excluded_nodes = set()  # Nodes to exclude from leak detection (pumps, reservoirs, tanks)
        self._load_model()
        self._load_excluded_nodes()
    
    def _load_model(self):
        """Load model, scaler và metadata"""
        try:
            model_dir = Path("models")
            # Try local model first, fallback to server model
            local_model_file = model_dir / "leak_detection_model_local.pkl"
            server_model_file = model_dir / "leak_detection_model.pkl"
            
            if local_model_file.exists():
                model_file = local_model_file
                logger.info(f"[OK] Using LOCAL model: {model_file}")
            elif server_model_file.exists():
                model_file = server_model_file
                logger.info(f"[OK] Using SERVER model: {model_file}")
            else:
                logger.warning(f"Model file not found: {model_file}")
                return
            
            scaler_file = model_dir / "scaler.pkl"
            metadata_file = model_dir / "model_metadata.json"
            
            # Load model
            with open(model_file, 'rb') as f:
                self.model = pickle.load(f)
            logger.info("[OK] Model loaded successfully")
            
            # Load scaler (if exists)
            if scaler_file.exists():
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("[OK] Scaler loaded successfully")
            else:
                logger.warning("Scaler not found - using features without scaling")
            
            # Load metadata
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                
                # Get feature columns
                if 'feature_cols' in self.metadata:
                    self.feature_cols = self.metadata['feature_cols']
                
                # Get optimal threshold if available
                # Note: best_threshold (0.92) is too high for real-world use
                # Using 0.1 (10%) for production - balanced between detection and false positives
                # This threshold provides reasonable detection rate (~2-3%) with acceptable confidence
                if 'best_threshold' in self.metadata:
                    # Use balanced threshold for production
                    # Original: self.threshold = self.metadata['best_threshold']  # 0.92 - too high
                    # Previous: self.threshold = 0.05  # 5% - too low, many false positives
                    self.threshold = 0.1  # 10% - balanced for production use
                elif 'optimal_threshold' in self.metadata:
                    self.threshold = self.metadata['optimal_threshold']
                else:
                    self.threshold = 0.1  # Default to 10% for production
                
                logger.info(f"[OK] Metadata loaded - Threshold: {self.threshold:.3f} (adjusted from {self.metadata.get('best_threshold', 'N/A')} for production balance)")
            else:
                logger.warning("Metadata file not found")
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.model = None
    
    def _load_excluded_nodes(self):
        """Load nodes to exclude from leak detection (reservoirs, tanks, pumps)"""
        try:
            # Load from metadata if available
            if self.metadata and 'reservoir_nodes' in self.metadata:
                excluded_from_metadata = set(str(n) for n in self.metadata['reservoir_nodes'])
                self.excluded_nodes.update(excluded_from_metadata)
                logger.info(f"[OK] Loaded {len(excluded_from_metadata)} excluded nodes from metadata")
            
            # Parse EPANET input file to get reservoirs and tanks
            inp_file = Path("epanetVip1.inp")
            if not inp_file.exists():
                inp_file = Path("epanet.inp")
            
            if inp_file.exists():
                import re
                with open(inp_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find RESERVOIRS section
                reservoir_match = re.search(r'\[RESERVOIRS\](.*?)(?=\[|\Z)', content, re.DOTALL | re.IGNORECASE)
                if reservoir_match:
                    reservoir_section = reservoir_match.group(1)
                    # Pattern: ID followed by Head value
                    reservoir_ids = re.findall(r'^(\w+)\s+', reservoir_section, re.MULTILINE)
                    for res_id in reservoir_ids:
                        self.excluded_nodes.add(str(res_id).strip())
                    logger.info(f"[OK] Found {len(reservoir_ids)} reservoirs: {reservoir_ids[:5]}...")
                
                # Find TANKS section
                tank_match = re.search(r'\[TANKS\](.*?)(?=\[|\Z)', content, re.DOTALL | re.IGNORECASE)
                if tank_match:
                    tank_section = tank_match.group(1)
                    # Pattern: ID followed by Elevation value
                    tank_ids = re.findall(r'^(\w+)\s+', tank_section, re.MULTILINE)
                    for tank_id in tank_ids:
                        self.excluded_nodes.add(str(tank_id).strip())
                    logger.info(f"[OK] Found {len(tank_ids)} tanks: {tank_ids[:5]}...")
                
                logger.info(f"[OK] Total excluded nodes: {len(self.excluded_nodes)}")
            else:
                logger.warning(f"EPANET input file not found: {inp_file}")
                
        except Exception as e:
            logger.warning(f"Error loading excluded nodes: {e}")
    
    def is_ready(self) -> bool:
        """Check if service is ready to use"""
        return self.model is not None
    
    def _load_topology_features(self):
        """Load topology features from network_topology.csv if available"""
        topology_file = Path("dataset/network_topology.csv")
        neighbor_map = {}
        topology_df = None
        
        if topology_file.exists():
            try:
                topology_df = pd.read_csv(topology_file)
                logger.info(f"[OK] Topology loaded: {len(topology_df)} nodes")
                
                # Build neighbor map from topology
                # Format 1: node_id, neighbors (comma-separated string)
                if 'neighbors' in topology_df.columns and 'node_id' in topology_df.columns:
                    for _, row in topology_df.iterrows():
                        node_id = str(row['node_id'])
                        neighbors_str = str(row['neighbors']) if pd.notna(row['neighbors']) else ''
                        if neighbors_str and neighbors_str != 'nan':
                            neighbors = [n.strip() for n in neighbors_str.split(',') if n.strip()]
                            neighbor_map[node_id] = neighbors
                            # Also add reverse connections
                            for neighbor in neighbors:
                                if neighbor not in neighbor_map:
                                    neighbor_map[neighbor] = []
                                if node_id not in neighbor_map[neighbor]:
                                    neighbor_map[neighbor].append(node_id)
                # Format 2: from_node, to_node (edge list)
                elif 'from_node' in topology_df.columns and 'to_node' in topology_df.columns:
                    for _, row in topology_df.iterrows():
                        from_node = str(row['from_node'])
                        to_node = str(row['to_node'])
                        if from_node not in neighbor_map:
                            neighbor_map[from_node] = []
                        if to_node not in neighbor_map:
                            neighbor_map[to_node] = []
                        if to_node not in neighbor_map[from_node]:
                            neighbor_map[from_node].append(to_node)
                        if from_node not in neighbor_map[to_node]:
                            neighbor_map[to_node].append(from_node)
            except Exception as e:
                logger.warning(f"Error loading topology: {e}")
        else:
            logger.warning(f"Topology file not found: {topology_file}")
        
        return neighbor_map, topology_df
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features từ simulation results
        Áp dụng feature engineering giống như training
        """
        if df.empty:
            return df
        
        df_fe = df.copy()
        
        # Group by scenario_id and node_id for rolling features
        if 'scenario_id' not in df_fe.columns:
            df_fe['scenario_id'] = 0  # Default scenario_id
        
        # Group by scenario_id and node_id
        g = df_fe.groupby(['scenario_id', 'node_id'], sort=False)
        
        # Basic temporal features
        if 'pressure_change' not in df_fe.columns:
            df_fe['pressure_change'] = g['pressure'].transform(lambda x: x.diff().fillna(0))
        
        if 'head_change' not in df_fe.columns:
            df_fe['head_change'] = g['head'].transform(lambda x: x.diff().fillna(0))
        
        # Moving averages
        if 'pressure_ma3' not in df_fe.columns:
            df_fe['pressure_ma3'] = g['pressure'].transform(lambda x: x.rolling(3, min_periods=1).mean())
            df_fe['pressure_ma5'] = g['pressure'].transform(lambda x: x.rolling(5, min_periods=1).mean())
            df_fe['head_ma3'] = g['head'].transform(lambda x: x.rolling(3, min_periods=1).mean())
            df_fe['head_ma5'] = g['head'].transform(lambda x: x.rolling(5, min_periods=1).mean())
        
        # Network-level features
        if 'network_pressure_mean' not in df_fe.columns:
            df_fe['network_pressure_mean'] = df_fe.groupby(['scenario_id', 'timestamp'])['pressure'].transform('mean')
            df_fe['network_pressure_std'] = df_fe.groupby(['scenario_id', 'timestamp'])['pressure'].transform('std').fillna(0)
            df_fe['network_demand_mean'] = df_fe.groupby(['scenario_id', 'timestamp'])['demand'].transform('mean')
        
        # Deviation features
        if 'pressure_deviation' not in df_fe.columns:
            df_fe['pressure_deviation'] = df_fe['pressure'] - df_fe['network_pressure_mean']
            df_fe['demand_deviation'] = df_fe.groupby(['scenario_id', 'node_id'])['demand'].transform(lambda x: x - x.mean())
        
        # Pressure/Head drops
        if 'pressure_drop' not in df_fe.columns:
            df_fe['pressure_drop'] = -df_fe['pressure_change'].clip(upper=0)
            df_fe['head_drop'] = -df_fe['head_change'].clip(upper=0)
        
        # Additional statistical features (rolling window 5)
        if 'pressure_std_5' not in df_fe.columns:
            df_fe['pressure_std_5'] = g['pressure'].transform(lambda x: x.rolling(5, min_periods=1).std().fillna(0))
            df_fe['head_std_5'] = g['head'].transform(lambda x: x.rolling(5, min_periods=1).std().fillna(0))
            df_fe['demand_std_5'] = g['demand'].transform(lambda x: x.rolling(5, min_periods=1).std().fillna(0))
        
        if 'pressure_min_5' not in df_fe.columns:
            df_fe['pressure_min_5'] = g['pressure'].transform(lambda x: x.rolling(5, min_periods=1).min())
            df_fe['pressure_max_5'] = g['pressure'].transform(lambda x: x.rolling(5, min_periods=1).max())
            df_fe['head_min_5'] = g['head'].transform(lambda x: x.rolling(5, min_periods=1).min())
            df_fe['head_max_5'] = g['head'].transform(lambda x: x.rolling(5, min_periods=1).max())
        
        # Acceleration features (second derivative)
        if 'pressure_acceleration' not in df_fe.columns:
            df_fe['pressure_acceleration'] = g['pressure_change'].transform(lambda x: x.diff().fillna(0))
            df_fe['head_acceleration'] = g['head_change'].transform(lambda x: x.diff().fillna(0))
        
        # Percentage change features
        if 'pressure_change_pct' not in df_fe.columns:
            df_fe['pressure_change_pct'] = (df_fe['pressure_change'] / (df_fe['pressure'].abs() + 1e-6))
            df_fe['head_change_pct'] = (df_fe['head_change'] / (df_fe['head'].abs() + 1e-6))
            df_fe['demand_change'] = g['demand'].transform(lambda x: x.diff().fillna(0))
            df_fe['demand_change_pct'] = (df_fe['demand_change'] / (df_fe['demand'].abs() + 1e-6))
        
        # Ratio features
        if 'pressure_demand_ratio' not in df_fe.columns:
            df_fe['pressure_demand_ratio'] = df_fe['pressure'] / (df_fe['demand'].abs() + 1e-6)
            df_fe['head_demand_ratio'] = df_fe['head'] / (df_fe['demand'].abs() + 1e-6)
        
        # 🚀 TOPOLOGY-BASED SPATIAL FEATURES (9 features)
        # These are required by the new model (39 features total)
        # ALWAYS create these features, even if they already exist (to ensure they're present)
        topology_features = [
            'neighbors_pressure_mean', 'neighbors_pressure_std', 'neighbors_head_mean',
            'neighbors_demand_mean', 'pressure_gradient', 'head_gradient',
            'node_degree', 'node_betweenness', 'node_elevation'
        ]
        
        # Check if any topology feature is missing
        missing_topology = [f for f in topology_features if f not in df_fe.columns]
        
        if missing_topology:
            # Load topology if available
            neighbor_map, topology_df = self._load_topology_features()
            
            # Initialize ALL topology features with defaults
            if 'neighbors_pressure_mean' not in df_fe.columns:
                df_fe['neighbors_pressure_mean'] = df_fe['pressure'].astype('float32')
            if 'neighbors_pressure_std' not in df_fe.columns:
                df_fe['neighbors_pressure_std'] = 0.0
            if 'neighbors_head_mean' not in df_fe.columns:
                df_fe['neighbors_head_mean'] = df_fe['head'].astype('float32')
            if 'neighbors_demand_mean' not in df_fe.columns:
                df_fe['neighbors_demand_mean'] = df_fe['demand'].astype('float32')
            if 'pressure_gradient' not in df_fe.columns:
                df_fe['pressure_gradient'] = 0.0
            if 'head_gradient' not in df_fe.columns:
                df_fe['head_gradient'] = 0.0
            if 'node_degree' not in df_fe.columns:
                df_fe['node_degree'] = 0
            if 'node_betweenness' not in df_fe.columns:
                df_fe['node_betweenness'] = 0.0
            if 'node_elevation' not in df_fe.columns:
                df_fe['node_elevation'] = 0.0
            
            # Merge topology features if available
            if topology_df is not None and 'node_id' in topology_df.columns:
                # Calculate node_degree from neighbors count
                if 'neighbors' in topology_df.columns:
                    topology_df['node_degree'] = topology_df['neighbors'].apply(
                        lambda x: len(str(x).split(',')) if pd.notna(x) and str(x) != 'nan' else 0
                    ).astype('int32')
                else:
                    # If no neighbors column, calculate from neighbor_map
                    if neighbor_map:
                        degree_dict = {node_id: len(neighbors) for node_id, neighbors in neighbor_map.items()}
                        topology_df['node_degree'] = topology_df['node_id'].astype(str).map(degree_dict).fillna(0).astype('int32')
                    else:
                        topology_df['node_degree'] = 0
                
                # Set default values for missing topology features
                if 'node_betweenness' not in topology_df.columns:
                    topology_df['node_betweenness'] = 0.0
                if 'node_elevation' not in topology_df.columns:
                    topology_df['node_elevation'] = 0.0
                
                # Merge topology features
                merge_df = topology_df[['node_id', 'node_degree', 'node_betweenness', 'node_elevation']].copy()
                merge_df['node_id'] = merge_df['node_id'].astype(str)
                
                # Merge with df_fe
                df_fe['node_id_str'] = df_fe['node_id'].astype(str)
                df_fe = df_fe.merge(merge_df, left_on='node_id_str', right_on='node_id', how='left', suffixes=('', '_topo'))
                df_fe['node_degree'] = df_fe['node_degree'].fillna(0).astype('int32')
                df_fe['node_betweenness'] = df_fe['node_betweenness'].fillna(0.0).astype('float32')
                df_fe['node_elevation'] = df_fe['node_elevation'].fillna(0.0).astype('float32')
                
                # Clean up temporary column
                if 'node_id_str' in df_fe.columns:
                    df_fe = df_fe.drop(columns=['node_id_str'])
                if 'node_id_topo' in df_fe.columns:
                    df_fe = df_fe.drop(columns=['node_id_topo'])
            
            # Compute neighbor features if neighbor_map is available
            if neighbor_map:
                # Group by timestamp for efficient processing
                for timestamp in df_fe['timestamp'].unique():
                    mask = df_fe['timestamp'] == timestamp
                    timestamp_df = df_fe[mask].copy()
                    
                    # Build lookup for this timestamp
                    node_lookup = {}
                    for _, row in timestamp_df.iterrows():
                        node_id = str(row['node_id'])
                        node_lookup[node_id] = {
                            'pressure': row['pressure'],
                            'head': row['head'],
                            'demand': row['demand']
                        }
                    
                    # Compute neighbor features
                    for idx in timestamp_df.index:
                        row = timestamp_df.loc[idx]
                        node_id = str(row['node_id'])
                        neighbors = neighbor_map.get(node_id, [])
                        
                        if neighbors:
                            neighbor_pressures = [node_lookup[n]['pressure'] for n in neighbors if n in node_lookup]
                            neighbor_heads = [node_lookup[n]['head'] for n in neighbors if n in node_lookup]
                            neighbor_demands = [node_lookup[n]['demand'] for n in neighbors if n in node_lookup]
                            
                            if neighbor_pressures:
                                df_fe.at[idx, 'neighbors_pressure_mean'] = np.mean(neighbor_pressures)
                                df_fe.at[idx, 'neighbors_pressure_std'] = np.std(neighbor_pressures) if len(neighbor_pressures) > 1 else 0.0
                                df_fe.at[idx, 'pressure_gradient'] = row['pressure'] - np.mean(neighbor_pressures)
                            else:
                                df_fe.at[idx, 'neighbors_pressure_mean'] = row['pressure']
                                df_fe.at[idx, 'neighbors_pressure_std'] = 0.0
                                df_fe.at[idx, 'pressure_gradient'] = 0.0
                            
                            if neighbor_heads:
                                df_fe.at[idx, 'neighbors_head_mean'] = np.mean(neighbor_heads)
                                df_fe.at[idx, 'head_gradient'] = row['head'] - np.mean(neighbor_heads)
                            else:
                                df_fe.at[idx, 'neighbors_head_mean'] = row['head']
                                df_fe.at[idx, 'head_gradient'] = 0.0
                            
                            if neighbor_demands:
                                df_fe.at[idx, 'neighbors_demand_mean'] = np.mean(neighbor_demands)
                            else:
                                df_fe.at[idx, 'neighbors_demand_mean'] = row['demand']
                        else:
                            # No neighbors - use current values
                            df_fe.at[idx, 'neighbors_pressure_mean'] = row['pressure']
                            df_fe.at[idx, 'neighbors_pressure_std'] = 0.0
                            df_fe.at[idx, 'neighbors_head_mean'] = row['head']
                            df_fe.at[idx, 'neighbors_demand_mean'] = row['demand']
                            df_fe.at[idx, 'pressure_gradient'] = 0.0
                            df_fe.at[idx, 'head_gradient'] = 0.0
        
        # Final check: Ensure all 9 topology features exist
        topology_features = [
            'neighbors_pressure_mean', 'neighbors_pressure_std', 'neighbors_head_mean',
            'neighbors_demand_mean', 'pressure_gradient', 'head_gradient',
            'node_degree', 'node_betweenness', 'node_elevation'
        ]
        for feat in topology_features:
            if feat not in df_fe.columns:
                logger.warning(f"Topology feature {feat} missing, creating with default value")
                if 'neighbors_pressure_mean' in feat or 'neighbors_head_mean' in feat or 'neighbors_demand_mean' in feat:
                    df_fe[feat] = df_fe.get('pressure', 0) if 'pressure' in feat else (df_fe.get('head', 0) if 'head' in feat else df_fe.get('demand', 0))
                elif 'degree' in feat:
                    df_fe[feat] = 0
                else:
                    df_fe[feat] = 0.0
        
        return df_fe
    
    def detect_leaks(
        self, 
        nodes_data: Dict[str, List[Dict[str, Any]]],
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect leaks từ simulation results
        
        Args:
            nodes_data: Dict với key là node_id, value là list of records
                       Mỗi record có: timestamp, pressure, head, demand
            threshold: Optional threshold override (default: use model threshold)
        
        Returns:
            Dict với:
            - success: bool
            - leaks: List of detected leaks
            - summary: Summary statistics
        """
        if not self.is_ready():
            return {
                "success": False,
                "error": "Model not loaded",
                "leaks": [],
                "summary": {}
            }
        
        try:
            # Convert nodes_data to DataFrame
            records = []
            for node_id, node_records in nodes_data.items():
                for record in node_records:
                    records.append({
                        'node_id': node_id,
                        'timestamp': record.get('timestamp', 0),
                        'pressure': record.get('pressure', 0),
                        'head': record.get('head', 0),
                        'demand': record.get('demand', 0)
                    })
            
            if not records:
                return {
                    "success": False,
                    "error": "No data provided",
                    "leaks": [],
                    "summary": {}
                }
            
            df = pd.DataFrame(records)
            
            # Prepare features
            df_fe = self.prepare_features(df)
            
            # Determine expected feature count from model
            expected_feature_count = 30  # Default for local model
            if hasattr(self.model, 'feature_names_') and self.model.feature_names_:
                expected_feature_count = len(self.model.feature_names_)
                logger.info(f"Model expects {expected_feature_count} features")
            
            # Base feature list (30 features) - for local model
            base_feature_list = [
                # Basic (3)
                'pressure', 'head', 'demand',
                # Moving averages (4)
                'pressure_ma3', 'pressure_ma5', 'head_ma3', 'head_ma5',
                # Temporal changes (4)
                'pressure_change', 'head_change', 'pressure_drop', 'head_drop',
                # Network-level spatial (5)
                'network_pressure_mean', 'network_pressure_std', 'network_demand_mean',
                'pressure_deviation', 'demand_deviation',
                # Statistical rolling (7)
                'pressure_std_5', 'head_std_5', 'demand_std_5',
                'pressure_min_5', 'pressure_max_5', 'head_min_5', 'head_max_5',
                # Acceleration (2)
                'pressure_acceleration', 'head_acceleration',
                # Percentage change (3)
                'pressure_change_pct', 'head_change_pct', 'demand_change_pct',
                # Ratio (2)
                'pressure_demand_ratio', 'head_demand_ratio'
            ]
            
            # Extended feature list (39 features) - for server model with topology features
            extended_feature_list = base_feature_list + [
                # Topology-based spatial (9) - Only for 39-feature model
                'neighbors_pressure_mean', 'neighbors_pressure_std', 'neighbors_head_mean',
                'neighbors_demand_mean', 'pressure_gradient', 'head_gradient',
                'node_degree', 'node_betweenness', 'node_elevation'
            ]
            
            # Select feature list based on model requirements
            if expected_feature_count == 39:
                full_feature_list = extended_feature_list
                logger.info("Using 39-feature list (with topology features)")
            else:
                full_feature_list = base_feature_list
                logger.info(f"Using {len(base_feature_list)}-feature list (local model)")
            
            # Check which features are available
            available_features = [f for f in full_feature_list if f in df_fe.columns]
            missing_features = [f for f in full_feature_list if f not in df_fe.columns]
            
            # Log feature status
            logger.info(f"Feature preparation: {len(available_features)}/{len(full_feature_list)} features available")
            if missing_features:
                logger.warning(f"Missing {len(missing_features)} features: {missing_features}")
                # Try to add missing features with default values
                for feat in missing_features:
                    if 'neighbors_pressure_mean' in feat:
                        df_fe[feat] = df_fe['pressure'].astype('float32') if 'pressure' in df_fe.columns else 0.0
                    elif 'neighbors_head_mean' in feat:
                        df_fe[feat] = df_fe['head'].astype('float32') if 'head' in df_fe.columns else 0.0
                    elif 'neighbors_demand_mean' in feat:
                        df_fe[feat] = df_fe['demand'].astype('float32') if 'demand' in df_fe.columns else 0.0
                    elif feat in ['neighbors_pressure_std', 'pressure_gradient', 'head_gradient', 'node_betweenness', 'node_elevation']:
                        df_fe[feat] = 0.0
                    elif feat == 'node_degree':
                        df_fe[feat] = 0
                    else:
                        logger.error(f"Cannot create default for missing feature: {feat}")
                        # Set to 0 as last resort
                        df_fe[feat] = 0.0
                
                # Re-check after adding defaults
                available_features = [f for f in full_feature_list if f in df_fe.columns]
                missing_features = [f for f in full_feature_list if f not in df_fe.columns]
                logger.info(f"After adding defaults: {len(available_features)}/{len(full_feature_list)} features available")
            
            # Ensure we have exactly the number of features the model expects
            if hasattr(self.model, 'feature_names_') and self.model.feature_names_:
                expected_count = len(self.model.feature_names_)
                
                # Use metadata feature_cols if available and matches expected count
                if self.feature_cols and len(self.feature_cols) == expected_count:
                    logger.info(f"Using metadata feature_cols ({len(self.feature_cols)} features)")
                    feature_list_to_use = [f for f in self.feature_cols if f in df_fe.columns]
                    missing_from_metadata = [f for f in self.feature_cols if f not in df_fe.columns]
                    
                    if missing_from_metadata:
                        logger.warning(f"Missing {len(missing_from_metadata)} features from metadata: {missing_from_metadata[:3]}...")
                        # Create missing features with defaults
                        for feat in missing_from_metadata:
                            if feat not in df_fe.columns:
                                df_fe[feat] = 0.0
                        feature_list_to_use = self.feature_cols
                    
                    if len(feature_list_to_use) == expected_count:
                        X = df_fe[feature_list_to_use].values
                        logger.info(f"Using {len(feature_list_to_use)} features from metadata")
                    else:
                        # Fallback to full_feature_list
                        if len(full_feature_list) == expected_count:
                            logger.info(f"Falling back to full_feature_list ({len(full_feature_list)} features)")
                            # Ensure all features exist
                            for feat in full_feature_list:
                                if feat not in df_fe.columns:
                                    df_fe[feat] = 0.0
                            X = df_fe[full_feature_list].values
                        else:
                            raise ValueError(f"Feature count mismatch: Expected {expected_count}, got {len(feature_list_to_use)}")
                else:
                    # Use full_feature_list (should match expected_count)
                    if len(full_feature_list) != expected_count:
                        logger.error(f"Feature list length ({len(full_feature_list)}) doesn't match model ({expected_count})")
                        raise ValueError(f"Feature list mismatch: {len(full_feature_list)} != {expected_count}")
                    
                    # Ensure all features exist
                    for feat in full_feature_list:
                        if feat not in df_fe.columns:
                            logger.warning(f"Creating missing feature: {feat}")
                            df_fe[feat] = 0.0
                    
                    X = df_fe[full_feature_list].values
                    logger.info(f"Using {len(full_feature_list)} features from full_feature_list")
            else:
                # Model doesn't have feature_names_, use metadata or full_feature_list
                if self.feature_cols:
                    X = df_fe[self.feature_cols].values
                    logger.info(f"Using {len(self.feature_cols)} features from metadata (no model feature_names_)")
                else:
                    X = df_fe[full_feature_list].values
                    logger.info(f"Using {len(full_feature_list)} features from full_feature_list (no model feature_names_)")
            
            # Scale features (if scaler exists)
            if self.scaler is not None:
                try:
                    X_scaled = self.scaler.transform(X)
                except Exception as e:
                    logger.warning(f"Scaling failed: {e}, using unscaled features")
                    X_scaled = X
            else:
                X_scaled = X
            
            # Predict
            use_threshold = threshold if threshold is not None else self.threshold
            proba = self.model.predict_proba(X_scaled)[:, 1]
            
            # Log probability statistics for debugging
            logger.info(f"Probability stats - Min: {proba.min():.3f}, Max: {proba.max():.3f}, Mean: {proba.mean():.3f}, Threshold: {use_threshold:.3f}")
            logger.info(f"Nodes with prob >= {use_threshold:.3f}: {(proba >= use_threshold).sum()} / {len(proba)}")
            
            # Log top probabilities for debugging
            top_probs = np.sort(proba)[::-1][:10]  # Top 10
            logger.info(f"Top 10 probabilities: {top_probs}")
            
            # Log feature statistics if probability is very low
            if proba.max() < 0.2:
                logger.warning(f"Very low probabilities detected (max: {proba.max():.3f}). Possible reasons:")
                logger.warning("  1. Simulation data is normal (no leaks) - this is expected")
                logger.warning("  2. Features may not match training data format")
                logger.warning("  3. Model may need retraining with real-world data")
            
            predictions = (proba >= use_threshold).astype(int)
            
            # Add predictions to dataframe
            df_fe['leak_probability'] = proba
            df_fe['predicted_leak'] = predictions
            
            # Get detected leaks
            leaks_df = df_fe[df_fe['predicted_leak'] == 1].copy()
            
            # Filter out excluded nodes (reservoirs, tanks, pumps)
            if len(self.excluded_nodes) > 0:
                initial_count = len(leaks_df)
                leaks_df = leaks_df[~leaks_df['node_id'].astype(str).isin(self.excluded_nodes)]
                filtered_count = initial_count - len(leaks_df)
                if filtered_count > 0:
                    logger.info(f"[OK] Filtered out {filtered_count} leaks from excluded nodes (reservoirs/tanks/pumps)")
            
            # Filter out supply nodes (demand < 0) - these are pump stations or supply points
            initial_count = len(leaks_df)
            leaks_df = leaks_df[leaks_df['demand'] >= 0]
            filtered_supply = initial_count - len(leaks_df)
            if filtered_supply > 0:
                logger.info(f"[OK] Filtered out {filtered_supply} leaks from supply nodes (demand < 0)")
            
            # Filter out very low probability leaks (likely false positives)
            # Minimum probability threshold: 5% for meaningful leaks
            min_probability_threshold = 0.05
            initial_count = len(leaks_df)
            leaks_df = leaks_df[leaks_df['leak_probability'] >= min_probability_threshold]
            filtered_low_prob = initial_count - len(leaks_df)
            if filtered_low_prob > 0:
                logger.info(f"[OK] Filtered out {filtered_low_prob} leaks with probability < {min_probability_threshold*100:.0f}% (likely false positives)")
            
            # Additional filter: Remove nodes with very low demand (< 0.001 m³/s = 1 L/s)
            # These are likely measurement noise or inactive nodes
            initial_count = len(leaks_df)
            leaks_df = leaks_df[leaks_df['demand'] >= 0.001]
            filtered_low_demand = initial_count - len(leaks_df)
            if filtered_low_demand > 0:
                logger.info(f"[OK] Filtered out {filtered_low_demand} leaks with demand < 0.001 m³/s (likely noise)")
            
            # Format results
            leaks = []
            for _, row in leaks_df.iterrows():
                # Calculate flow: positive for demand nodes (consumption)
                # Flow = demand (already in m³/s, positive for consumption)
                demand_m3s = float(row['demand'])
                flow_lps = demand_m3s * 1000  # Convert to L/s, keep positive
                
                leaks.append({
                    "node_id": str(row['node_id']),
                    "timestamp": float(row['timestamp']),
                    "probability": float(row['leak_probability']),
                    "pressure": float(row['pressure']),
                    "head": float(row['head']),
                    "demand": demand_m3s,
                    "flow": flow_lps  # Add flow field (positive for consumption)
                })
            
            # Remove duplicate nodes: keep only the leak with highest probability for each node
            # This prevents showing the same node multiple times at different timestamps
            unique_leaks = {}
            for leak in leaks:
                node_id = leak['node_id']
                if node_id not in unique_leaks or leak['probability'] > unique_leaks[node_id]['probability']:
                    unique_leaks[node_id] = leak
            
            # Convert back to list and sort by probability (highest first)
            leaks = list(unique_leaks.values())
            leaks.sort(key=lambda x: x['probability'], reverse=True)
            
            # Log duplicate removal
            if len(leaks_df) > len(leaks):
                logger.info(f"[OK] Removed {len(leaks_df) - len(leaks)} duplicate node entries (kept highest probability for each node)")
            
            # Summary
            # Calculate unique nodes count (for detection rate calculation)
            unique_nodes_count = df_fe['node_id'].nunique() if 'node_id' in df_fe.columns else len(df_fe)
            
            summary = {
                "total_records": len(df_fe),  # Total node-timestamp pairs
                "total_unique_nodes": unique_nodes_count,  # Total unique nodes
                "detected_leaks": len(leaks),  # Number of unique nodes with leaks
                "detection_rate": len(leaks) / unique_nodes_count if unique_nodes_count > 0 else 0,  # Leaks / Unique nodes
                "records_with_leaks": len(leaks_df),  # Total records (node-timestamp) with leaks (before deduplication)
                "threshold_used": use_threshold,
                "avg_probability": float(proba.mean()) if len(proba) > 0 else 0,
                "max_probability": float(proba.max()) if len(proba) > 0 else 0
            }
            
            return {
                "success": True,
                "leaks": leaks,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error detecting leaks: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "leaks": [],
                "summary": {}
            }
    
    def detect_leaks_from_simulation_result(
        self, 
        simulation_result: Dict[str, Any],
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect leaks từ SimulationResult object
        
        Args:
            simulation_result: SimulationResult dict từ EPANET service
            threshold: Optional threshold override
        
        Returns:
            Dict với detected leaks
        """
        if not self.is_ready():
            return {
                "success": False,
                "error": "Model not loaded",
                "leaks": []
            }
        
        try:
            nodes_results = simulation_result.get('nodes_results', {})
            
            # Convert to format expected by detect_leaks
            nodes_data = {}
            for node_id, node_data in nodes_results.items():
                if isinstance(node_data, list):
                    nodes_data[node_id] = node_data
                elif isinstance(node_data, dict):
                    # Convert dict to list of records
                    records = []
                    timestamps = node_data.get('timestamps', [])
                    pressures = node_data.get('pressures', [])
                    heads = node_data.get('heads', [])
                    demands = node_data.get('demands', [])
                    
                    for i in range(len(timestamps)):
                        records.append({
                            'timestamp': timestamps[i],
                            'pressure': pressures[i] if i < len(pressures) else 0,
                            'head': heads[i] if i < len(heads) else 0,
                            'demand': demands[i] if i < len(demands) else 0
                        })
                    nodes_data[node_id] = records
            
            return self.detect_leaks(nodes_data, threshold)
            
        except Exception as e:
            logger.error(f"Error detecting leaks from simulation result: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "leaks": []
            }

# Global instance
leak_detection_service = LeakDetectionService()

