/**
 * Redux slice cho Leak Detection
 */
import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { leakDetectionService, Leak, LeakSummary, LeakDetectionStatus } from '../../services/leakDetection';

interface LeakDetectionState {
  leaks: Leak[];
  summary: LeakSummary | null;
  isDetecting: boolean;
  isReady: boolean;
  error: string | null;
  threshold: number | null;
}

const initialState: LeakDetectionState = {
  leaks: [],
  summary: null,
  isDetecting: false,
  isReady: false,
  error: null,
  threshold: null,
};

/**
 * Async thunk để check service status
 */
export const checkLeakDetectionStatus = createAsyncThunk(
  'leakDetection/checkStatus',
  async (_, { rejectWithValue }) => {
    try {
      const status = await leakDetectionService.checkStatus();
      return status;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to check status');
    }
  }
);

/**
 * Async thunk để detect leaks từ simulation result
 */
export const detectLeaksFromSimulation = createAsyncThunk(
  'leakDetection/detectFromSimulation',
  async (params: { simulationResult: any; threshold?: number }, { rejectWithValue, getState }) => {
    try {
      // Get threshold from state if not provided
      const state = getState() as { leakDetection: LeakDetectionState };
      const threshold = params.threshold ?? state.leakDetection.threshold ?? undefined;
      
      const result = await leakDetectionService.detectLeaksFromSimulation(
        params.simulationResult,
        threshold
      );
      return result;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to detect leaks');
    }
  }
);

/**
 * Async thunk để detect leaks từ nodes data
 */
export const detectLeaks = createAsyncThunk(
  'leakDetection/detect',
  async (nodesData: Record<string, Array<{
    timestamp: number;
    pressure: number;
    head: number;
    demand: number;
  }>>, { rejectWithValue }) => {
    try {
      const result = await leakDetectionService.detectLeaks(nodesData);
      return result;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to detect leaks');
    }
  }
);

const leakDetectionSlice = createSlice({
  name: 'leakDetection',
  initialState,
  reducers: {
    clearLeaks: (state) => {
      state.leaks = [];
      state.summary = null;
      state.error = null;
    },
    setLeaks: (state, action: PayloadAction<Leak[]>) => {
      state.leaks = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setThreshold: (state, action: PayloadAction<number>) => {
      state.threshold = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      // Check status
      .addCase(checkLeakDetectionStatus.pending, (state) => {
        state.error = null;
      })
      .addCase(checkLeakDetectionStatus.fulfilled, (state, action) => {
        state.isReady = action.payload.ready;
        state.threshold = action.payload.threshold || null;
        if (!action.payload.ready) {
          state.error = action.payload.message;
        }
      })
      .addCase(checkLeakDetectionStatus.rejected, (state, action) => {
        state.isReady = false;
        state.error = action.payload as string;
      })
      // Detect leaks from simulation
      .addCase(detectLeaksFromSimulation.pending, (state) => {
        state.isDetecting = true;
        state.error = null;
      })
      .addCase(detectLeaksFromSimulation.fulfilled, (state, action) => {
        state.isDetecting = false;
        state.leaks = action.payload.leaks;
        state.summary = action.payload.summary;
        state.error = null;
      })
      .addCase(detectLeaksFromSimulation.rejected, (state, action) => {
        state.isDetecting = false;
        state.error = action.payload as string;
        state.leaks = [];
        state.summary = null;
      })
      // Detect leaks from nodes data
      .addCase(detectLeaks.pending, (state) => {
        state.isDetecting = true;
        state.error = null;
      })
      .addCase(detectLeaks.fulfilled, (state, action) => {
        state.isDetecting = false;
        state.leaks = action.payload.leaks;
        state.summary = action.payload.summary;
        state.error = null;
      })
      .addCase(detectLeaks.rejected, (state, action) => {
        state.isDetecting = false;
        state.error = action.payload as string;
        state.leaks = [];
        state.summary = null;
      });
  },
});

export const { clearLeaks, setLeaks, setError, setThreshold } = leakDetectionSlice.actions;
export default leakDetectionSlice.reducer;

