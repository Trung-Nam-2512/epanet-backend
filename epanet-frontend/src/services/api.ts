import { SimulationParams, CustomTimeParams, SimulationResult } from './types';

// API Configuration
// Dùng relative URL - tự động dùng cùng domain, chỉ đổi port
const API_BASE_URL = typeof window !== 'undefined' ? window.location.origin.replace(':1437', ':1438') : '';

// API Response Types
interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

interface NetworkTopologyResponse {
  nodes: Array<{
    id: string;
    x_coord: number;
    y_coord: number;
    demand: number;
  }>;
  pipes: Array<{
    id: string;
    from_node: string;
    to_node: string;
    length: number;
    diameter: number;
    roughness: number;
    status: string;
  }>;
}

class ApiService {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const config = { ...defaultOptions, ...options };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Get network topology data
  async getNetworkTopology(): Promise<ApiResponse<NetworkTopologyResponse>> {
    return this.request<NetworkTopologyResponse>('/api/v1/network/topology');
  }

  // Get real-time simulation data
  async getRealTimeSimulation(params: SimulationParams): Promise<any> {
    const url = `${this.baseURL}/api/v1/scada/simulation-with-realtime`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message || 'Simulation failed');
      }

      // API returns { success, message, simulation_result, scada_summary }
      // Return the full response structure
      return {
        success: data.success,
        message: data.message,
        simulation_result: data.simulation_result,
        scada_summary: data.scada_summary
      };
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Get custom time simulation data
  async getCustomTimeSimulation(params: CustomTimeParams): Promise<SimulationResult> {
    const url = `${this.baseURL}/api/v1/scada/simulation-with-custom-time`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message || 'Custom time simulation failed');
      }

      // Backend returns { success, message, simulation_result, scada_summary }
      // Return the full response structure similar to real-time simulation
      return {
        success: data.success,
        message: data.message,
        simulation_result: data.simulation_result,
      };
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Get simulation status
  async getSimulationStatus(runId: string): Promise<SimulationResult> {
    const response = await this.request<SimulationResult>(`/api/v1/simulation/status/${runId}`);
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to get simulation status');
    }

    return response.data;
  }

  // Get SCADA data
  async getScadaData(stationCodes: string, hoursBack: number = 24): Promise<any> {
    const response = await this.request<any>('/api/v1/scada/data', {
      method: 'POST',
      body: JSON.stringify({
        station_codes: stationCodes,
        hours_back: hoursBack
      }),
    });

    if (!response.success) {
      throw new Error(response.message || 'Failed to get SCADA data');
    }

    return response.data;
  }
}

// Create and export the API service instance
export const apiService = new ApiService();
