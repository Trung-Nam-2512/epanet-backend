// API Types
export interface SimulationParams {
  station_codes: string[];
  hours_back: number;
  duration: number;
  hydraulic_timestep: number;
  report_timestep: number;
}

export interface CustomTimeParams {
  station_codes: string[];
  from_date: string;
  to_date: string;
  duration: number;
  hydraulic_timestep?: number;
  report_timestep?: number;
}

export interface NodeData {
  node_id: string;
  pressure: number;
  head: number;
  demand: number;
  flow: number;
}

export interface PipeData {
  timestamp: string;
  flow: number;
}

export interface SimulationResult {
  success: boolean;
  message: string;
  simulation_result: {
    run_id: string;
    status: string;
    timestamp: string;
    duration: number;
    nodes_results: Record<string, NodeData[]>;
    pipes_results: Record<string, PipeData[]>;
    pumps_results: Record<string, any[]>;
  };
}

// Map Types
export interface MapCoordinates {
  lng: number;
  lat: number;
}

export interface NetworkNode {
  id: string;
  coordinates: MapCoordinates;
  pressure: number;
  head: number;
  demand: number;  // Actual demand từ simulation results
  base_demand: number;  // Base demand từ file INP - dùng để so sánh
  flow: number;
}

export interface NetworkPipe {
  id: string;
  from_node: string;
  to_node: string;
  flow: number;
  velocity: number;
  headloss: number;
}

// Redux State Types
export interface NetworkState {
  data: SimulationResult | null;
  loading: boolean;
  error: string | null;
  selectedNode: string | null;
}

export interface SimulationState {
  isRunning: boolean;
  parameters: SimulationParams | null;
  results: SimulationResult | null;
}

