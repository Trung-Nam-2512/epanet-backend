/**
 * Leak Detection Service
 * Service để gọi API phát hiện rò rỉ
 */

// Dùng relative URL - tự động dùng cùng domain, chỉ đổi port
const LEAK_DETECTION_API_BASE = typeof window !== 'undefined' ? window.location.origin.replace(':1437', ':1438') : '';
const LEAK_DETECTION_API = `${LEAK_DETECTION_API_BASE}/api/v1/leak-detection`;

export interface Leak {
  node_id: string;
  timestamp: number;
  probability: number;
  pressure: number;
  head: number;
  demand: number;
  flow?: number; // Optional flow field (L/s)
}

export interface LeakSummary {
  total_records: number;
  total_unique_nodes?: number; // Optional: số nodes duy nhất
  detected_leaks: number;
  detection_rate: number;
  records_with_leaks?: number; // Optional: số records có leaks (trước khi deduplicate)
  threshold_used: number;
  avg_probability: number;
  max_probability: number;
}

export interface LeakDetectionResponse {
  success: boolean;
  leaks: Leak[];
  summary: LeakSummary;
}

export interface LeakDetectionStatus {
  success: boolean;
  ready: boolean;
  message: string;
  threshold?: number;
}

class LeakDetectionService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${LEAK_DETECTION_API}${endpoint}`;
    
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const config = { ...defaultOptions, ...options };

    try {
      const response = await fetch(url, config);
      
      // Check content type before parsing
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Leak detection API returned non-JSON response:', {
          status: response.status,
          statusText: response.statusText,
          contentType: contentType,
          url: url,
          preview: text.substring(0, 200)
        });
        throw new Error(`API returned HTML instead of JSON. Status: ${response.status}. This usually means the backend is not running or the endpoint is incorrect.`);
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Leak detection API request failed:', error);
      throw error;
    }
  }

  /**
   * Kiểm tra trạng thái của leak detection service
   */
  async checkStatus(): Promise<LeakDetectionStatus> {
    try {
      const response = await this.request<LeakDetectionStatus>('/status');
      return response;
    } catch (error) {
      console.error('Error checking leak detection status:', error);
      return {
        success: false,
        ready: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Phát hiện rò rỉ từ nodes data
   * @param nodesData Dict với key là node_id, value là list of records
   */
  async detectLeaks(nodesData: Record<string, Array<{
    timestamp: number;
    pressure: number;
    head: number;
    demand: number;
  }>>): Promise<LeakDetectionResponse> {
    const response = await this.request<{ success: boolean; data: LeakDetectionResponse }>(
      '/detect',
      {
        method: 'POST',
        body: JSON.stringify({ nodes_data: nodesData }),
      }
    );
    
    if (!response.success) {
      throw new Error('Leak detection failed');
    }
    
    return response.data;
  }

  /**
   * Phát hiện rò rỉ từ simulation result
   * @param simulationResult SimulationResult từ EPANET service
   * @param threshold Optional threshold override
   */
  async detectLeaksFromSimulation(
    simulationResult: any,
    threshold?: number
  ): Promise<LeakDetectionResponse> {
    const requestBody: any = { simulation_result: simulationResult };
    if (threshold !== undefined) {
      requestBody.threshold = threshold;
    }
    
    const response = await this.request<{ success: boolean; data: LeakDetectionResponse }>(
      '/detect-from-simulation',
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
      }
    );
    
    if (!response.success) {
      throw new Error('Leak detection failed');
    }
    
    return response.data;
  }
}

export const leakDetectionService = new LeakDetectionService();

