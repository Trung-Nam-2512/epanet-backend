import React, { useEffect, useState, useRef } from 'react';
import { useSelector } from 'react-redux';
import { useMap } from '../../hooks/useMap';
import { NetworkNode, NetworkPipe } from '../../services/types';
import { useSimulation } from '../../hooks/useApi';
import { generateNetworkLayout } from '../../services/networkData';
import { updatePipesData } from '../../services/mapbox';
import { RootState } from '../../store';
import NodeTooltip from './NodeTooltip';
import PipeTooltip from './PipeTooltip';
import Legend from './Legend';

interface MapContainerProps {
    navigationState?: {
        targetNodeId: string | null;
        shouldZoom: boolean;
        shouldHighlight: boolean;
    };
    onNavigationComplete?: () => void;
}

const MapContainer: React.FC<MapContainerProps> = ({
    navigationState,
    onNavigationComplete
}) => {
    const { data, selectedNode, runSimulation } = useSimulation();
    const [nodes, setNodes] = useState<NetworkNode[]>([]);
    const [pipes, setPipes] = useState<NetworkPipe[]>([]);
    const [selectedNodeData, setSelectedNodeData] = useState<NetworkNode | null>(null);
    const [tooltipVisible, setTooltipVisible] = useState(false);
    const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | undefined>(undefined);
    const mapRef = useRef<any>(null);

    // Get leaks from Redux store for map visualization
    const leaks = useSelector((state: RootState) => state.leakDetection.leaks);

    // Cache simulation data in ref to ensure it's always available
    const simulationDataRef = useRef<any>(null);

    // Update ref whenever data changes
    useEffect(() => {
        if (data?.simulation_result) {
            simulationDataRef.current = data.simulation_result;
        }
    }, [data]);

    // Pipe tooltip state
    const [selectedPipeId, setSelectedPipeId] = useState<string | null>(null);
    const [selectedPipeProperties, setSelectedPipeProperties] = useState<any>(null);
    const [pipeTooltipVisible, setPipeTooltipVisible] = useState(false);
    const [pipeTooltipPosition, setPipeTooltipPosition] = useState<{ x: number; y: number } | undefined>(undefined);

    // NOTE: Removed auto-run simulation on mount
    // Simulation will only run when user clicks "Run Simulation" button in Sidebar
    // This ensures all DOM elements are fully rendered before simulation data arrives

    // Load network layout on component mount
    useEffect(() => {
        const loadNetwork = async () => {
            try {
                const { nodes, pipes } = await generateNetworkLayout();
                setNodes(nodes);
                setPipes(pipes);
            } catch (error) {
                // Error loading network
            }
        };

        loadNetwork();
    }, []);

    // Update nodes and pipes with simulation data
    useEffect(() => {
        if (data && data.success && data.simulation_result) {
            // Update nodes
            setNodes(prevNodes => {
                const simulationResults = data.simulation_result.nodes_results || {};
                const simulationKeys = Object.keys(simulationResults);

                // Create a lookup map for simulation data with normalized keys (both string and number)
                const simulationLookup = new Map<string, any[]>();
                simulationKeys.forEach(key => {
                    const normalizedKey = String(key);
                    simulationLookup.set(normalizedKey, simulationResults[key]);
                    // Also store with numeric key if applicable
                    const numKey = parseInt(normalizedKey, 10);
                    if (!isNaN(numKey)) {
                        simulationLookup.set(String(numKey), simulationResults[key]);
                    }
                });

                let updatedCount = 0;
                let notFoundCount = 0;
                const notFoundNodes: string[] = [];

                const updatedNodes = prevNodes.map(node => {
                    // Try multiple ID formats to find matching simulation data
                    const nodeIdStr = String(node.id);
                    const nodeIdNum = !isNaN(Number(nodeIdStr)) ? Number(nodeIdStr) : null;
                    const nodeIdNumStr = nodeIdNum !== null ? String(nodeIdNum) : null;

                    // Try to find data with multiple strategies
                    let nodeData = simulationLookup.get(nodeIdStr) ||
                        (nodeIdNumStr ? simulationLookup.get(nodeIdNumStr) : undefined) ||
                        simulationResults[node.id] ||
                        simulationResults[nodeIdStr] ||
                        (nodeIdNum !== null ? simulationResults[nodeIdNum] : undefined);

                    if (nodeData && Array.isArray(nodeData) && nodeData.length > 0) {
                        const latestData = nodeData[nodeData.length - 1];
                        updatedCount++;

                        return {
                            ...node,
                            pressure: Number(latestData.pressure) || 0,
                            head: Number(latestData.head) || 0,
                            demand: Number(latestData.demand) || 0,  // Actual demand từ simulation
                            base_demand: node.base_demand || 0,  // Giữ nguyên base_demand từ INP
                            flow: Number(latestData.flow) || 0,
                        };
                    } else {
                        // Node not found in simulation results
                        notFoundCount++;
                        if (notFoundCount <= 10) {
                            notFoundNodes.push(`${node.id} (type: ${typeof node.id})`);
                        }
                        // Keep node but ensure values are numbers (in case they're undefined)
                        return {
                            ...node,
                            pressure: Number(node.pressure) || 0,
                            head: Number(node.head) || 0,
                            demand: Number(node.demand) || 0,
                            base_demand: node.base_demand || 0,  // Giữ nguyên base_demand
                            flow: Number(node.flow) || 0,
                        };
                    }
                });

                return updatedNodes;
            });

            // Update pipes
            setPipes(prevPipes => {
                const updatedPipes = prevPipes.map(pipe => {
                    // Try both string and number keys for pipe ID
                    const pipeData = data.simulation_result.pipes_results[pipe.id] ||
                        data.simulation_result.pipes_results[pipe.id.toString()];

                    if (pipeData && pipeData.length > 0) {
                        const latestData = pipeData[pipeData.length - 1];
                        return {
                            ...pipe,
                            flow: latestData.flow || 0,
                        };
                    }
                    return pipe;
                });
                return updatedPipes;
            });
        }
    }, [data]);

    // Handle navigation from dashboard
    useEffect(() => {
        if (navigationState?.targetNodeId && navigationState.shouldZoom && nodes.length > 0) {
            const targetNode = nodes.find(node => node.id === navigationState.targetNodeId);

            if (targetNode && mapRef.current) {

                // Zoom to the target node
                mapRef.current.flyTo({
                    center: [targetNode.coordinates.lng, targetNode.coordinates.lat],
                    zoom: 18,
                    duration: 2000
                });

                // Highlight the node by clicking it programmatically
                setTimeout(() => {
                    // Calculate tooltip position based on node coordinates on map
                    if (mapRef.current) {
                        const point = mapRef.current.project([targetNode.coordinates.lng, targetNode.coordinates.lat]);
                        const clickEvent = { x: point.x, y: point.y };
                        handleNodeClick(String(targetNode.id), clickEvent);
                    } else {
                        handleNodeClick(String(targetNode.id));
                    }

                    if (onNavigationComplete) {
                        onNavigationComplete();
                    }
                }, 1000);
            }
        }
    }, [navigationState, nodes, onNavigationComplete]);

    const handleNodeClick = (nodeId: string, clickEvent?: { x: number; y: number }) => {
        // Use ref cache if data is not available (fallback)
        const simResult = data?.simulation_result || simulationDataRef.current;

        // ALWAYS find the node from current nodes state (which has the latest simulation data)
        // Try multiple ID formats to ensure we find the node
        const nodeIdStr = String(nodeId);
        const nodeIdNum = !isNaN(Number(nodeIdStr)) ? Number(nodeIdStr) : null;

        // First try to find in current nodes state
        const currentNode = nodes.find(n => {
            const nId = String(n.id);
            const nIdNum = !isNaN(Number(nId)) ? Number(nId) : null;
            return nId === nodeIdStr ||
                n.id === nodeId ||
                (nodeIdNum !== null && nIdNum === nodeIdNum) ||
                String(parseInt(nId, 10)) === String(parseInt(nodeIdStr, 10));
        });

        let nodeToShow: NetworkNode | null = null;

        if (currentNode) {
            // If node found but has no data, try to get from simulation results directly
            if (currentNode.pressure === 0 && currentNode.head === 0 && simResult?.nodes_results) {
                const simResults = simResult.nodes_results;
                const nodeData = simResults[nodeIdStr] || simResults[nodeId] ||
                    (nodeIdNum !== null ? simResults[nodeIdNum] : undefined);

                if (nodeData && Array.isArray(nodeData) && nodeData.length > 0) {
                    const latestData = nodeData[nodeData.length - 1];
                    nodeToShow = {
                        ...currentNode,
                        pressure: Number(latestData.pressure) || 0,
                        head: Number(latestData.head) || 0,
                        demand: Number(latestData.demand) || 0,
                        flow: Number(latestData.flow) || 0,
                    };
                } else {
                    nodeToShow = currentNode;
                }
            } else {
                nodeToShow = currentNode;
            }
        } else {
            // Try to get data directly from Redux store (or cached ref) and find base node data
            if (simResult?.nodes_results) {
                const simulationResults = simResult.nodes_results;
                // Try different key formats to get simulation data
                const nodeData = simulationResults[nodeIdStr] ||
                    simulationResults[nodeId] ||
                    (nodeIdNum !== null ? simulationResults[nodeIdNum] : undefined);

                if (nodeData && Array.isArray(nodeData) && nodeData.length > 0) {
                    const latestData = nodeData[nodeData.length - 1];

                    // Find base node data from nodes (for coordinates, etc.)
                    const baseNode = nodes.find(n => String(n.id) === nodeIdStr || String(n.id) === nodeId);

                    if (baseNode) {
                        // Merge base node with simulation data
                        nodeToShow = {
                            ...baseNode,
                            pressure: Number(latestData.pressure) || 0,
                            head: Number(latestData.head) || 0,
                            demand: Number(latestData.demand) || 0,
                            flow: Number(latestData.flow) || 0,
                        };
                    } else {
                        // If base node not found, create minimal node from simulation data
                        nodeToShow = {
                            id: nodeIdStr,
                            coordinates: { lat: 0, lng: 0 }, // Will need coordinates from elsewhere
                            pressure: Number(latestData.pressure) || 0,
                            head: Number(latestData.head) || 0,
                            demand: Number(latestData.demand) || 0,
                            base_demand: 0, // No base demand available
                            flow: Number(latestData.flow) || 0,
                        };
                    }
                }
            }
        }

        if (!nodeToShow) {
            // Try to find any node with this ID as fallback
            const fallbackNode = nodes.find(n => String(n.id) === nodeIdStr || String(n.id) === nodeId);
            if (fallbackNode) {
                nodeToShow = fallbackNode;
            }
        }

        if (nodeToShow) {
            setSelectedNodeData(nodeToShow);
            setTooltipVisible(true);
            if (clickEvent) {
                setTooltipPosition(clickEvent);
            }
        }
    };

    const handleTooltipClose = () => {
        setTooltipVisible(false);
        setSelectedNodeData(null);
    };

    const handlePipeClick = (pipeId: string, properties: any, clickEvent?: { x: number; y: number }) => {
        setSelectedPipeId(pipeId);
        setSelectedPipeProperties(properties);
        setPipeTooltipVisible(true);
        if (clickEvent) {
            setPipeTooltipPosition(clickEvent);
        }
        // Close node tooltip if open
        setTooltipVisible(false);
    };

    const handlePipeTooltipClose = () => {
        setPipeTooltipVisible(false);
        setSelectedPipeId(null);
        setSelectedPipeProperties(null);
    };

    const { map, isMapLoaded } = useMap({
        containerId: 'map-container',
        token: process.env.REACT_APP_MAPBOX_TOKEN || 'pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', // Use env token or fallback
        nodes,
        pipes,
        leaks: leaks.map(l => ({ node_id: l.node_id, probability: l.probability })),
        onNodeClick: handleNodeClick,
        onPipeClick: handlePipeClick,
    });

    // Store map reference for navigation
    useEffect(() => {
        if (map) {
            mapRef.current = map;
        }
    }, [map]);

    // Update Mapbox layer when pipes data changes
    useEffect(() => {
        if (map && pipes.length > 0 && nodes.length > 0) {
            updatePipesData(map, pipes, nodes);
        }
    }, [map, pipes, nodes]);

    return (
        <div style={{ position: 'relative', height: '100vh' }}>
            <div
                id="map-container"
                style={{
                    width: '100%',
                    height: '100%',
                    background: '#f0f0f0'
                }}
            />

            {/* Map loading indicator */}
            {!isMapLoaded && (
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    background: 'rgba(255, 255, 255, 0.9)',
                    padding: '20px',
                    borderRadius: '8px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}>
                    <div style={{ textAlign: 'center' }}>
                        <div>Loading Map...</div>
                        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                            Initializing Mapbox
                        </div>
                    </div>
                </div>
            )}

            {/* Node Tooltip */}
            <NodeTooltip
                node={selectedNodeData}
                visible={tooltipVisible}
                onClose={handleTooltipClose}
                position={tooltipPosition}
            />

            {/* Pipe Tooltip */}
            <PipeTooltip
                pipeId={selectedPipeId}
                properties={selectedPipeProperties}
                visible={pipeTooltipVisible}
                onClose={handlePipeTooltipClose}
                position={pipeTooltipPosition}
            />

            {/* Legend */}
            <Legend />
        </div>
    );
};

export default MapContainer;
