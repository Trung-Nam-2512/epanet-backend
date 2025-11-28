import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { fetchSimulationData, fetchCustomTimeSimulation, setSelectedNode } from '../store/slices/networkSlice';
import { SimulationParams } from '../services/types';

export const useSimulation = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { data, loading, error, selectedNode } = useSelector((state: RootState) => state.network);

  const runSimulation = (params: SimulationParams) => {
    console.log('Running simulation with params:', params);
    dispatch(fetchSimulationData(params));
  };

  const runCustomTimeSimulation = (params: any) => {
    console.log('Running custom time simulation with params:', params);
    dispatch(fetchCustomTimeSimulation(params));
  };

  const selectNode = (nodeId: string | null) => {
    dispatch(setSelectedNode(nodeId));
  };

  // Debug: Log data changes
  React.useEffect(() => {
    if (data) {
      console.log('Simulation data updated:', {
        success: data.success,
        hasSimulationResult: !!data.simulation_result,
        nodesResultsKeys: data.simulation_result ? Object.keys(data.simulation_result.nodes_results || {}) : [],
        pipesResultsKeys: data.simulation_result ? Object.keys(data.simulation_result.pipes_results || {}) : []
      });
    }
  }, [data]);

  return {
    data,
    loading,
    error,
    selectedNode,
    runSimulation,
    runCustomTimeSimulation,
    selectNode,
  };
};

