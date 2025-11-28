import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { SimulationParams, SimulationState } from '../../services/types';

const initialState: SimulationState = {
  isRunning: false,
  parameters: null,
  results: null,
};

const simulationSlice = createSlice({
  name: 'simulation',
  initialState,
  reducers: {
    startSimulation: (state, action: PayloadAction<SimulationParams>) => {
      state.isRunning = true;
      state.parameters = action.payload;
    },
    stopSimulation: (state) => {
      state.isRunning = false;
    },
    setResults: (state, action: PayloadAction<any>) => {
      state.results = action.payload;
      state.isRunning = false;
    },
    clearResults: (state) => {
      state.results = null;
      state.parameters = null;
    },
  },
});

export const { startSimulation, stopSimulation, setResults, clearResults } = simulationSlice.actions;
export default simulationSlice.reducer;

