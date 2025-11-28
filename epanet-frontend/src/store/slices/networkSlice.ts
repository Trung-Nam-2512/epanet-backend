import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiService } from '../../services/api';
import { SimulationParams, SimulationResult, NetworkState } from '../../services/types';

// Async thunk for fetching simulation data
export const fetchSimulationData = createAsyncThunk(
  'network/fetchSimulationData',
  async (params: SimulationParams, { rejectWithValue }) => {
    try {
      const response = await apiService.getRealTimeSimulation(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || error.message);
    }
  }
);

// Async thunk for fetching custom time simulation
export const fetchCustomTimeSimulation = createAsyncThunk(
  'network/fetchCustomTimeSimulation',
  async (params: any, { rejectWithValue }) => {
    try {
      const response = await apiService.getCustomTimeSimulation(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || error.message);
    }
  }
);

const initialState: NetworkState = {
  data: null,
  loading: false,
  error: null,
  selectedNode: null,
};

const networkSlice = createSlice({
  name: 'network',
  initialState,
  reducers: {
    setSelectedNode: (state, action: PayloadAction<string | null>) => {
      state.selectedNode = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    clearData: (state) => {
      state.data = null;
      state.selectedNode = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch simulation data
      .addCase(fetchSimulationData.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSimulationData.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
        state.error = null;
      })
      .addCase(fetchSimulationData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Fetch custom time simulation
      .addCase(fetchCustomTimeSimulation.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCustomTimeSimulation.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
        state.error = null;
      })
      .addCase(fetchCustomTimeSimulation.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { setSelectedNode, clearError, clearData } = networkSlice.actions;
export default networkSlice.reducer;

