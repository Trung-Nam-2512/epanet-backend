import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { 
  initializeMap, 
  addNodesLayer, 
  addPipesLayer, 
  fitMapToBounds, 
  addNodeClickHandler, 
  addPipeClickHandler,
  updateNodesData,
  updatePipesData
} from '../services/mapbox';
import { NetworkNode, NetworkPipe } from '../services/types';

interface UseMapProps {
  containerId: string;
  token: string;
  nodes?: NetworkNode[];
  pipes?: NetworkPipe[];
  leaks?: Array<{ node_id: string; probability: number }>;
  onNodeClick?: (nodeId: string, clickEvent?: { x: number; y: number }) => void;
  onPipeClick?: (pipeId: string, properties: any, clickEvent?: { x: number; y: number }) => void;
}

export const useMap = ({ containerId, token, nodes, pipes, leaks, onNodeClick, onPipeClick }: UseMapProps) => {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [layersInitialized, setLayersInitialized] = useState(false);

  // Initialize map
  useEffect(() => {
    if (!mapRef.current) {
      try {
        mapRef.current = initializeMap(containerId, token);
        
        mapRef.current.on('load', () => {
          setIsMapLoaded(true);
        });

        mapRef.current.on('error', (error) => {
          console.error('Map error:', error);
          // Check if it's a token-related error
          if (error.error && error.error.message) {
            if (error.error.message.includes('token') || error.error.message.includes('unauthorized')) {
              console.error('Mapbox token error. Please check your REACT_APP_MAPBOX_TOKEN environment variable.');
            }
          }
        });
      } catch (error) {
        console.error('Error initializing map:', error);
      }
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        setLayersInitialized(false);
      }
    };
  }, [containerId, token]);

  // Add/update layers when nodes change
  useEffect(() => {
    if (!mapRef.current || !isMapLoaded || !nodes || nodes.length === 0) {
      return;
    }

    // First time: add layers
    if (!layersInitialized) {
      // Add pipes layer first (below nodes)
      if (pipes && pipes.length > 0) {
        addPipesLayer(mapRef.current, pipes, nodes);
      }
      
      // Add nodes layer
      addNodesLayer(mapRef.current, nodes, leaks || []);
      
      // Add click handlers
      // IMPORTANT: Only pass nodeId, not the node object, to avoid closure issues
      // The handler will find the latest node data from state
      if (onNodeClick) {
        addNodeClickHandler(mapRef.current, (nodeId, clickEvent) => {
          // Always pass nodeId as string to ensure consistent matching
          onNodeClick(nodeId, clickEvent);
        });
      }

      if (onPipeClick) {
        addPipeClickHandler(mapRef.current, onPipeClick);
      }
      
      setLayersInitialized(true);
      
      // Auto-fit map to bounds disabled - removed to prevent automatic zoom on load
      // setTimeout(() => {
      //   fitMapToBounds(mapRef.current!, nodes);
      // }, 100);
    } else {
      // Subsequent updates: update both nodes and pipes data (for real-time updates)
      updateNodesData(mapRef.current, nodes, leaks || []);
      if (pipes && pipes.length > 0) {
        // Check if pipes layer exists, if not add it
        if (!mapRef.current.getLayer('pipes-layer')) {
          console.log('Pipes layer missing, adding it now...');
          addPipesLayer(mapRef.current, pipes, nodes);
        } else {
          updatePipesData(mapRef.current, pipes, nodes);
        }
      }
    }
  }, [nodes, pipes, leaks, isMapLoaded, layersInitialized, onNodeClick, onPipeClick]);

  return {
    map: mapRef.current,
    isMapLoaded,
    markers: [],  // No markers anymore, using layers
  };
};