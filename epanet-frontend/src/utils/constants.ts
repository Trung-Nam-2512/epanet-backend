// Environment variables with fallbacks
export const MAPBOX_TOKEN = process.env.REACT_APP_MAPBOX_TOKEN || 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example';
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api/v1/scada';

// Map configuration
export const MAP_CONFIG = {
  center: [106.6297, 10.8231] as [number, number], // Ho Chi Minh City
  zoom: 12,
  minZoom: 8,
  maxZoom: 18,
  style: 'mapbox://styles/mapbox/streets-v11',
};

// Default simulation parameters - đã fix theo chuẩn
export const DEFAULT_SIMULATION_PARAMS = {
  station_codes: ['13085'],
  hours_back: 1,
  duration: 1,
  hydraulic_timestep: 1,
  report_timestep: 1
};

// Color schemes
export const PRESSURE_COLORS = {
  high: '#4caf50',    // Green - > 30m
  medium: '#ff9800',   // Orange - 20-30m
  low: '#ff5722',      // Red - 10-20m
  veryLow: '#f44336', // Dark red - < 10m
};

export const FLOW_COLORS = {
  high: '#2196f3',     // Blue - > 50L/s
  medium: '#00bcd4',   // Cyan - 20-50L/s
  low: '#4caf50',      // Green - 5-20L/s
  veryLow: '#9e9e9e',  // Gray - < 5L/s
};

