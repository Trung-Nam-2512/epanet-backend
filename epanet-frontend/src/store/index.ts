
import { configureStore } from '@reduxjs/toolkit';
import networkReducer from './slices/networkSlice';
import simulationReducer from './slices/simulationSlice';
import leakDetectionReducer from './slices/leakDetectionSlice';

export const store = configureStore({
  reducer: {
    network: networkReducer,
    simulation: simulationReducer,
    leakDetection: leakDetectionReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

