import { NetworkNode, NetworkPipe } from './types';
import { apiService } from './api';

export const loadNetworkTopology = async (): Promise<{ nodes: NetworkNode[], pipes: NetworkPipe[] }> => {
  try {
    const response = await apiService.getNetworkTopology();
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to load network topology');
    }

    const { nodes: apiNodes, pipes: apiPipes } = response.data;

    // Convert API data to frontend format using REAL coordinates from epanet.inp
    const nodes: NetworkNode[] = apiNodes.map((node: any) => {
      return {
        id: node.id,
        coordinates: {
          lng: node.x_coord, // Use actual X coordinate from epanet.inp
          lat: node.y_coord  // Use actual Y coordinate from epanet.inp
        },
        pressure: 0, // Will be updated by simulation
        head: 0,
        demand: node.demand || 0,  // Demand từ [JUNCTIONS] (thường là 0)
        base_demand: node.base_demand || 0,  // Base demand từ [DEMANDS] - dùng để so sánh
        flow: 0
      };
    });

    const pipes: NetworkPipe[] = apiPipes.map((pipe: any) => ({
      id: pipe.id,
      from_node: pipe.from_node,
      to_node: pipe.to_node,
      length: pipe.length,
      diameter: pipe.diameter,
      roughness: pipe.roughness,
      status: pipe.status,
      flow: 0, // Will be updated by simulation
      velocity: 0,
      headloss: 0
    }));

    return { nodes, pipes };

  } catch (error) {
    console.error('Error loading network topology:', error);
    // Fallback to empty data
    return { nodes: [], pipes: [] };
  }
};

// Legacy function for backward compatibility
export const generateNetworkLayout = async (): Promise<{ nodes: NetworkNode[], pipes: NetworkPipe[] }> => {
  return await loadNetworkTopology();
};

