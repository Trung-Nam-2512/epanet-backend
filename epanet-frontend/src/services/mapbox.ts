import mapboxgl from 'mapbox-gl';
import { MapCoordinates, NetworkNode, NetworkPipe } from './types';
import { DEFAULT_DEMAND_THRESHOLDS } from './demandColorConfig';

// Mapbox configuration
export const MAPBOX_CONFIG = {
  style: 'mapbox://styles/mapbox/streets-v11',
  center: [106.607, 10.877] as [number, number],
  zoom: 15,  // Increased from 18 for higher zoom level
  minZoom: 14,
  maxZoom: 22,
};

// Initialize map
export const initializeMap = (container: string, token: string): mapboxgl.Map => {
  mapboxgl.accessToken = token;
  
  const map = new mapboxgl.Map({
    container,
    style: MAPBOX_CONFIG.style,
    center: MAPBOX_CONFIG.center,
    zoom: MAPBOX_CONFIG.zoom,
    minZoom: MAPBOX_CONFIG.minZoom,
    maxZoom: MAPBOX_CONFIG.maxZoom,
  });

  // Add navigation controls
  map.addControl(new mapboxgl.NavigationControl(), 'top-right');
  
  // Add fullscreen control
  map.addControl(new mapboxgl.FullscreenControl(), 'top-right');

  return map;
};

/**
 * Get demand ratio color based on actual/base demand comparison
 * 
 * LOGIC: So sánh Actual Demand (từ simulation) với Base Demand (từ file INP)
 * 
 * Ngưỡng và ý nghĩa:
 * 
 * 🔴 ĐỎ ĐẬM (> 150%): 
 *    - Actual demand > 1.5x base demand
 *    - Cảnh báo: Có thể có rò rỉ lớn, sự cố nghiêm trọng, hoặc nhu cầu thực tế tăng đột biến
 * 
 * 🟠 CAM/ĐỎ (> 120%): 
 *    - Actual demand > 1.2x base demand  
 *    - Cảnh báo: Demand cao hơn dự kiến, có thể có rò rỉ nhỏ hoặc nhu cầu tăng
 * 
 * 🟢 XANH LÁ (80-120%): 
 *    - Actual demand trong khoảng 80-120% base demand
 *    - TỐT: Demand ở mức bình thường, hệ thống hoạt động ổn định
 * 
 * 🔵 XANH DƯƠNG (50-80%): 
 *    - Actual demand chỉ còn 50-80% base demand
 *    - CHÚ Ý: Demand thấp, có thể do:
 *      + Giờ thấp điểm (bình thường)
 *      + Van đóng một phần
 *      + Cần kiểm tra xem có bất thường không
 * 
 * 🟡 XANH VÀNG (actual = 0):
 *    - Actual demand = 0 (bất kể base_demand)
 *    - CHÚ Ý: Không có demand, áp dụng cho:
 *      + Ban đầu khi chưa chạy simulation (tất cả nodes)
 *      + Node có demand = 0 sau simulation
 * 
 * 🟡 XANH VÀNG (0-50%): 
 *    - Actual demand > 0 nhưng < 50% base demand
 *    - CHÚ Ý: Demand rất thấp, có thể có vấn đề:
 *      + Van đóng hoàn toàn
 *      + Đường ống tắc/bị hỏng
 *      + Rò rỉ lớn ở upstream
 * 
 * 🔴 ĐỎ ĐẬM (base_demand = 0, actual > 0):
 *    - Node không được thiết kế để có demand nhưng lại có demand
 *    - Cảnh báo: Có demand bất thường
 */
export const getDemandRatioColor = (actualDemand: number, baseDemand: number): string => {
  const absActual = Math.abs(actualDemand);
  const absBase = Math.abs(baseDemand);
  
  // Ưu tiên: Nếu actual_demand = 0, hiển thị màu vàng (chú ý)
  // Áp dụng cho cả trường hợp ban đầu (chưa chạy simulation) và khi demand = 0
  if (absActual === 0) {
    return '#cddc39'; // Lime/Yellow-green - Chú ý (demand = 0)
  }
  
  // Nếu base_demand = 0 nhưng actual_demand > 0 -> Có demand bất thường (đỏ)
  if (!absBase || absBase === 0) {
    return '#d32f2f'; // Dark red - Cảnh báo
  }
  
  // Tính tỷ lệ: actual / base
  const ratio = absActual / absBase;
  
  // Phân loại màu sắc dựa trên tỷ lệ demand:
  if (ratio > 1.5) {
    // > 150% base demand - 🔴 Đỏ đậm: Demand quá cao
    return '#d32f2f'; // Dark red
  } else if (ratio > 1.2) {
    // 120-150% base demand - 🟠 Cam/Đỏ: Demand cao, cần chú ý
    return '#ff5722'; // Red/Orange
  } else if (ratio > 0.8) {
    // 80-120% base demand - 🟢 Xanh lá: Demand bình thường
    return '#4caf50'; // Green
  } else if (ratio > 0.5) {
    // 50-80% base demand - 🔵 Xanh dương: Demand thấp
    return '#2196f3'; // Blue
  } else {
    // 0-50% base demand - 🟡 Xanh vàng: Demand rất thấp (bao gồm cả = 0)
    return '#cddc39'; // Lime/Yellow-green
  }
};

// Get pressure color based on value - TEMPORARILY DISABLED
// Color coding will be enabled after ML model training with real leak data
export const getPressureColor = (pressure: number): string => {
  // Return neutral blue color for all nodes until ML model is trained
  return '#2196f3'; // Blue - neutral color
  
  // Original color logic (commented out):
  // if (pressure > 30) return '#4caf50'; // Green
  // if (pressure > 20) return '#ff9800'; // Orange
  // if (pressure > 10) return '#ff5722'; // Red
  // if (pressure > 0) return '#9c27b0';  // Purple
  // return '#2196f3'; // Blue
};

/**
 * Get leak color based on probability
 * Red: probability >= 0.8 (High)
 * Orange: probability >= 0.6 (Medium)
 * Gold: probability < 0.6 (Low)
 */
export const getLeakColor = (probability: number): string => {
  if (probability >= 0.8) return '#d32f2f'; // Red - High probability
  if (probability >= 0.6) return '#ff5722'; // Orange - Medium probability
  return '#ffc107'; // Gold - Low probability
};

/**
 * Get node color - Leak color takes priority over demand ratio color
 * If node has leak, use leak color. Otherwise, use demand ratio color.
 */
export const getNodeColor = (
  node: NetworkNode, 
  leaks: Array<{ node_id: string; probability: number }> = []
): string => {
  // Check if node has leak (try multiple ID formats for matching)
  const nodeIdStr = String(node.id);
  const leak = leaks.find(l => {
    const leakNodeId = String(l.node_id);
    return leakNodeId === nodeIdStr || 
           leakNodeId === node.id ||
           (nodeIdStr && leakNodeId === nodeIdStr);
  });
  
  if (leak) {
    // Use leak color (priority)
    return getLeakColor(leak.probability);
  }
  
  // Fallback to demand ratio color
  return getDemandRatioColor(node.demand || 0, node.base_demand || 0);
};

// Get flow color based on value - TEMPORARILY DISABLED
// Color coding will be enabled after ML model training with real leak data
export const getFlowColor = (flow: number): string => {
  // Return neutral orange color for all pipes until ML model is trained
  return '#FF6B35'; // Orange-red - neutral color
  
  // Original color logic (commented out):
  // const absFlow = Math.abs(flow);
  // // High flow: Red (risk)
  // if (absFlow > 1.0) return '#d32f2f';  // Dark red
  // if (absFlow > 0.5) return '#f44336';  // Red
  // if (absFlow > 0.2) return '#ff9800';  // Orange
  // if (absFlow > 0.1) return '#ffc107';  // Amber
  // if (absFlow > 0.05) return '#4caf50'; // Green
  // if (absFlow > 0.01) return '#2196f3'; // Blue
  // return '#FF6B35';  // Orange-red (thay vì gray) - pipes luôn có màu đẹp
};

// Get flow line width based on value
export const getFlowLineWidth = (flow: number, baseWidth: number = 4): number => {
  const absFlow = Math.abs(flow);
  if (absFlow > 1.0) return baseWidth * 3;   // 12px
  if (absFlow > 0.5) return baseWidth * 2.5; // 10px
  if (absFlow > 0.2) return baseWidth * 2;   // 8px
  if (absFlow > 0.1) return baseWidth * 1.5; // 6px
  if (absFlow > 0.05) return baseWidth;      // 4px
  return baseWidth * 0.8;                    // 3.2px (thay vì 0.5)
};

// Add nodes as a Mapbox layer (circle layer)
export const addNodesLayer = (
  map: mapboxgl.Map, 
  nodes: NetworkNode[],
  leaks: Array<{ node_id: string; probability: number }> = []
): void => {
  // Remove existing layers/sources if they exist
  if (map.getLayer('nodes-layer')) {
    map.removeLayer('nodes-layer');
  }
  if (map.getSource('nodes')) {
    map.removeSource('nodes');
  }

  // Create GeoJSON features for nodes
  const features = nodes.map(node => ({
    type: 'Feature' as const,
    geometry: {
      type: 'Point' as const,
      coordinates: [node.coordinates.lng, node.coordinates.lat]
    },
    properties: {
      id: node.id,
      pressure: node.pressure,
      head: node.head,
      demand: node.demand,
      base_demand: node.base_demand || 0,
      flow: node.flow,
      // Use getNodeColor which prioritizes leak color over demand ratio color
      color: getNodeColor(node, leaks)
    }
  }));

  const geojson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: features
  };

  // Add source
  map.addSource('nodes', {
    type: 'geojson',
    data: geojson
  });

  // Add circle layer for nodes
  map.addLayer({
    id: 'nodes-layer',
    type: 'circle',
    source: 'nodes',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14, 8,   // At zoom 14: radius 8px
        18, 15,  // At zoom 18: radius 15px
        22, 20   // At zoom 22: radius 20px
      ],
      'circle-color': ['get', 'color'],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
      'circle-opacity': 0.9
    }
  });

  // Add labels for nodes
  map.addLayer({
    id: 'nodes-labels',
    type: 'symbol',
    source: 'nodes',
    layout: {
      'text-field': ['get', 'id'],
      'text-size': 10,
      'text-offset': [0, -2],
      'text-anchor': 'top'
    },
    paint: {
      'text-color': '#000000',
      'text-halo-color': '#ffffff',
      'text-halo-width': 2
    },
    minzoom: 17  // Only show labels at high zoom
  });
};

// Add pipes as a Mapbox layer (line layer)
export const addPipesLayer = (map: mapboxgl.Map, pipes: NetworkPipe[], nodes: NetworkNode[]): void => {
  console.log(`Adding pipes layer: ${pipes.length} pipes, ${nodes.length} nodes`);
  
  // Remove existing layers/sources if they exist
  if (map.getLayer('pipes-layer')) {
    map.removeLayer('pipes-layer');
  }
  if (map.getSource('pipes')) {
    map.removeSource('pipes');
  }

  // Create node coordinates lookup
  const nodeCoords = new Map<string, [number, number]>();
  nodes.forEach(node => {
    nodeCoords.set(node.id, [node.coordinates.lng, node.coordinates.lat]);
  });

  // Create GeoJSON features for pipes
  const features = pipes.map(pipe => {
    const fromCoords = nodeCoords.get(pipe.from_node);
    const toCoords = nodeCoords.get(pipe.to_node);

    if (!fromCoords || !toCoords) {
      return null;
    }

    const flow = pipe.flow || 0;
    return {
      type: 'Feature' as const,
      geometry: {
        type: 'LineString' as const,
        coordinates: [fromCoords, toCoords]
      },
      properties: {
        id: pipe.id,
        from_node: pipe.from_node,
        to_node: pipe.to_node,
        flow: flow,
        velocity: pipe.velocity || 0,
        headloss: pipe.headloss || 0,
        color: getFlowColor(flow),
        lineWidth: getFlowLineWidth(flow, 2)
      }
    };
  }).filter(f => f !== null);

  console.log(`Created ${features.length} pipe features from ${pipes.length} pipes`);

  const geojson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: features as GeoJSON.Feature[]
  };

  // Add source
  map.addSource('pipes', {
    type: 'geojson',
    data: geojson
  });

  // Add line layer for pipes (with dynamic color and width)
  map.addLayer({
    id: 'pipes-layer',
    type: 'line',
    source: 'pipes',
    layout: {
      'line-join': 'round',
      'line-cap': 'round'
    },
    paint: {
      'line-color': ['get', 'color'],  // Dynamic color based on flow
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14, ['*', ['get', 'lineWidth'], 0.8],   // At zoom 14: multiply by 0.8
        18, ['*', ['get', 'lineWidth'], 1.5],   // At zoom 18: multiply by 1.5
        22, ['*', ['get', 'lineWidth'], 2.5]    // At zoom 22: multiply by 2.5
      ],
      'line-opacity': 0.9
    }
  });

  console.log('Pipes layer added successfully');
};

// Update nodes data (for real-time updates)
export const updateNodesData = (
  map: mapboxgl.Map, 
  nodes: NetworkNode[],
  leaks: Array<{ node_id: string; probability: number }> = []
): void => {
  const source = map.getSource('nodes') as mapboxgl.GeoJSONSource;
  if (!source) {
    return;
  }

  const features = nodes.map(node => ({
    type: 'Feature' as const,
    geometry: {
      type: 'Point' as const,
      coordinates: [node.coordinates.lng, node.coordinates.lat]
    },
    properties: {
      id: node.id,
      pressure: node.pressure,
      head: node.head,
      demand: node.demand || 0,
      base_demand: node.base_demand || 0,
      flow: node.flow,
      // Use getNodeColor which prioritizes leak color over demand ratio color
      color: getNodeColor(node, leaks)
    }
  }));

  const geojson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: features
  };

  source.setData(geojson);
};

// Update pipes data (for real-time updates)
export const updatePipesData = (map: mapboxgl.Map, pipes: NetworkPipe[], nodes: NetworkNode[]): void => {
  const source = map.getSource('pipes') as mapboxgl.GeoJSONSource;
  if (!source) {
    return;
  }

  // Create node coordinates lookup
  const nodeCoords = new Map<string, [number, number]>();
  nodes.forEach(node => {
    nodeCoords.set(node.id, [node.coordinates.lng, node.coordinates.lat]);
  });

  // Create GeoJSON features for pipes
  const features = pipes.map(pipe => {
    const fromCoords = nodeCoords.get(pipe.from_node);
    const toCoords = nodeCoords.get(pipe.to_node);

    if (!fromCoords || !toCoords) {
      return null;
    }

    const flow = pipe.flow || 0;
    return {
      type: 'Feature' as const,
      geometry: {
        type: 'LineString' as const,
        coordinates: [fromCoords, toCoords]
      },
      properties: {
        id: pipe.id,
        from_node: pipe.from_node,
        to_node: pipe.to_node,
        flow: flow,
        velocity: pipe.velocity || 0,
        headloss: pipe.headloss || 0,
        color: getFlowColor(flow),
        lineWidth: getFlowLineWidth(flow, 2)
      }
    };
  }).filter(f => f !== null);

  const geojson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: features as GeoJSON.Feature[]
  };

  source.setData(geojson);
};

// Fit map to bounds
export const fitMapToBounds = (map: mapboxgl.Map, nodes: NetworkNode[]): void => {
  if (nodes.length === 0) {
    return;
  }

  const bounds = new mapboxgl.LngLatBounds();
  
  let minLng = Infinity, maxLng = -Infinity;
  let minLat = Infinity, maxLat = -Infinity;
  
  nodes.forEach(node => {
    bounds.extend([node.coordinates.lng, node.coordinates.lat]);
    minLng = Math.min(minLng, node.coordinates.lng);
    maxLng = Math.max(maxLng, node.coordinates.lng);
    minLat = Math.min(minLat, node.coordinates.lat);
    maxLat = Math.max(maxLat, node.coordinates.lat);
  });

  const paddingSize = 50;
  
  map.fitBounds(bounds, {
    padding: paddingSize,
    maxZoom: 20,
    duration: 1000
  });

  setTimeout(() => {
    const currentZoom = map.getZoom();
    if (currentZoom < 18) {
      map.setZoom(18);
    }
  }, 1100);
};

// Add click handler to nodes
export const addNodeClickHandler = (
  map: mapboxgl.Map,
  onNodeClick: (nodeId: string, clickEvent?: { x: number; y: number }) => void
): void => {
  // Change cursor on hover
  map.on('mouseenter', 'nodes-layer', () => {
    map.getCanvas().style.cursor = 'pointer';
  });

  map.on('mouseleave', 'nodes-layer', () => {
    map.getCanvas().style.cursor = '';
  });

  // Handle click
  map.on('click', 'nodes-layer', (e) => {
    if (e.features && e.features.length > 0) {
      const nodeId = e.features[0].properties?.id;
      if (nodeId) {
        // Get click position relative to map container
        const mapContainer = map.getContainer();
        const rect = mapContainer.getBoundingClientRect();
        const clickEvent = {
          x: e.point.x,
          y: e.point.y
        };
        onNodeClick(nodeId, clickEvent);
      }
    }
  });
};

// Add click handler to pipes
export const addPipeClickHandler = (
  map: mapboxgl.Map,
  onPipeClick: (pipeId: string, properties: any, clickEvent?: { x: number; y: number }) => void
): void => {
  // Change cursor on hover
  map.on('mouseenter', 'pipes-layer', () => {
    map.getCanvas().style.cursor = 'pointer';
  });

  map.on('mouseleave', 'pipes-layer', () => {
    map.getCanvas().style.cursor = '';
  });

  // Handle click
  map.on('click', 'pipes-layer', (e) => {
    if (e.features && e.features.length > 0) {
      const pipeId = e.features[0].properties?.id;
      const properties = e.features[0].properties;
      if (pipeId) {
        const clickEvent = {
          x: e.point.x,
          y: e.point.y
        };
        onPipeClick(pipeId, properties, clickEvent);
      }
    }
  });
};

// Dummy functions for backward compatibility (no longer needed)
export const createNodeMarker = () => null;
export const clearAllMarkers = () => {};
export const addMarkerClickHandler = () => {};
export const addPipeLines = () => {}; // Old function, replaced by addPipesLayer
export const getPipeColor = getFlowColor;