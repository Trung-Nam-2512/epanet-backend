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
            console.log('📦 Cached simulation data in ref');
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
                console.log('Loading network topology...');
                const { nodes, pipes } = await generateNetworkLayout();
                console.log('Loaded nodes:', nodes.length, 'pipes:', pipes.length);
                // console.log('Sample node:', nodes[0]);
                // console.log('Sample pipe:', pipes[0]);
                // console.log('First 5 pipes:', pipes.slice(0, 5));
                setNodes(nodes);
                setPipes(pipes);
            } catch (error) {
                console.error('Error loading network:', error);
            }
        };

        loadNetwork();
    }, []);

    // Update nodes and pipes with simulation data
    useEffect(() => {
        if (data && data.success && data.simulation_result) {
            console.log('Processing simulation data:', data.simulation_result);
            console.log('Nodes results keys:', Object.keys(data.simulation_result.nodes_results || {}));
            console.log('Pipes results keys:', Object.keys(data.simulation_result.pipes_results || {}));

            // Update nodes
            setNodes(prevNodes => {
                const simulationResults = data.simulation_result.nodes_results || {};
                const simulationKeys = Object.keys(simulationResults);
                console.log('🔄 Updating nodes with simulation data...');
                console.log('Available node IDs in simulation results:', simulationKeys.slice(0, 20));
                console.log('Current nodes in state:', prevNodes.map(n => ({ id: n.id, type: typeof n.id })).slice(0, 20));

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
                        
                        // Only log first few updates to avoid console spam
                        if (updatedCount <= 5) {
                            console.log(`✅ Updated node ${node.id} (${nodeIdStr}):`, {
                                pressure: latestData.pressure,
                                head: latestData.head,
                                demand: latestData.demand,
                                flow: latestData.flow
                            });
                        }

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
                
                if (notFoundCount > 0) {
                    console.log(`⚠️ ${notFoundCount} nodes not found in simulation results (first 10):`, notFoundNodes);
                    console.log(`Sample simulation keys:`, simulationKeys.slice(0, 10));
                    console.log(`Sample node IDs from state:`, prevNodes.slice(0, 10).map(n => `${n.id} (${typeof n.id})`));
                }
                
                console.log(`✅ Updated ${updatedCount} out of ${prevNodes.length} nodes with simulation data`);
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
                        console.log(`Updated pipe ${pipe.id}:`, latestData);
                        return {
                            ...pipe,
                            flow: latestData.flow || 0,
                        };
                    }
                    return pipe;
                });
                console.log('Updated pipes with simulation data:', updatedPipes.slice(0, 3));
                return updatedPipes;
            });
        } else {
            console.log('No simulation data available:', { data, success: data?.success, simulation_result: data?.simulation_result });
        }
    }, [data]);

    // Handle navigation from dashboard
    useEffect(() => {
        if (navigationState?.targetNodeId && navigationState.shouldZoom && nodes.length > 0) {
            const targetNode = nodes.find(node => node.id === navigationState.targetNodeId);

            console.log('Navigation triggered:', {
                targetNodeId: navigationState.targetNodeId,
                targetNode: targetNode,
                mapRef: mapRef.current,
                nodesLength: nodes.length
            });

            if (targetNode && mapRef.current) {
                console.log('Navigating to node:', targetNode.id, 'at coordinates:', targetNode.coordinates);

                // Zoom to the target node
                mapRef.current.flyTo({
                    center: [targetNode.coordinates.lng, targetNode.coordinates.lat],
                    zoom: 18,
                    duration: 2000
                });

                // Highlight the node by clicking it programmatically
                setTimeout(() => {
                    console.log('Programmatically clicking node:', targetNode.id);

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
            } else {
                console.log('Navigation failed - missing targetNode or mapRef:', {
                    targetNode: !!targetNode,
                    mapRef: !!mapRef.current
                });
            }
        }
    }, [navigationState, nodes, onNavigationComplete]);

    const handleNodeClick = (nodeId: string, clickEvent?: { x: number; y: number }) => {
        console.log('=== handleNodeClick ===');
        console.log('Clicked node ID:', nodeId, typeof nodeId);
        console.log('Current nodes state length:', nodes.length);
        
        // Use ref cache if data is not available (fallback)
        const simResult = data?.simulation_result || simulationDataRef.current;
        console.log('Has simulation data (from hook):', !!data?.simulation_result);
        console.log('Has simulation data (from ref):', !!simulationDataRef.current);
        console.log('Using simulation data:', !!simResult);

        // Check if node exists in simulation results (use cached data if needed)
        if (simResult?.nodes_results) {
            const simKeys = Object.keys(simResult.nodes_results);
            const hasInSim = simKeys.includes(String(nodeId)) || simKeys.includes(nodeId);
            console.log(`Node ${nodeId} in simulation results:`, hasInSim);
            if (hasInSim) {
                const simData = simResult.nodes_results[String(nodeId)] || 
                               simResult.nodes_results[nodeId];
                if (simData && Array.isArray(simData) && simData.length > 0) {
                    console.log(`Simulation data for node ${nodeId}:`, simData[simData.length - 1]);
                }
            } else {
                console.log(`Available simulation keys (first 30):`, simKeys.slice(0, 30));
            }
        }

        // ALWAYS find the node from current nodes state (which has the latest simulation data)
        // Try multiple ID formats to ensure we find the node
        const nodeIdStr = String(nodeId);
        const nodeIdNum = !isNaN(Number(nodeIdStr)) ? Number(nodeIdStr) : null;
        
        // Debug: Check all nodes with similar IDs
        const similarNodes = nodes.filter(n => {
            const nId = String(n.id);
            return nId.includes(nodeIdStr) || nodeIdStr.includes(nId) || 
                   String(n.id) === nodeId || n.id === nodeId;
        });
        console.log(`Nodes matching ${nodeIdStr}:`, similarNodes.map(n => ({
            id: n.id,
            type: typeof n.id,
            pressure: n.pressure,
            head: n.head
        })));
        
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
            console.log('✅ Found node in current state:', currentNode.id, 'type:', typeof currentNode.id);
            console.log('Node values from state:', {
                pressure: currentNode.pressure,
                head: currentNode.head,
                demand: currentNode.demand,
                flow: currentNode.flow
            });
            
            // If node found but has no data, try to get from simulation results directly
            if (currentNode.pressure === 0 && currentNode.head === 0 && simResult?.nodes_results) {
                console.log('⚠️ Node found but has zero values, trying simulation data directly...');
                const simResults = simResult.nodes_results;
                const nodeData = simResults[nodeIdStr] || simResults[nodeId] ||
                                (nodeIdNum !== null ? simResults[nodeIdNum] : undefined);
                
                if (nodeData && Array.isArray(nodeData) && nodeData.length > 0) {
                    const latestData = nodeData[nodeData.length - 1];
                    console.log('✅ Found simulation data for node with zero values:', latestData);
                    nodeToShow = {
                        ...currentNode,
                        pressure: Number(latestData.pressure) || 0,
                        head: Number(latestData.head) || 0,
                        demand: Number(latestData.demand) || 0,
                        flow: Number(latestData.flow) || 0,
                    };
                } else {
                    console.log(`❌ No simulation data found for node ${nodeIdStr} even though node exists`);
                    nodeToShow = currentNode;
                }
            } else {
                nodeToShow = currentNode;
            }
        } else {
            console.log('⚠️ Node not found in state, trying to get from simulation data directly');
            
            // Try to get data directly from Redux store (or cached ref) and find base node data
            if (simResult?.nodes_results) {
                const simulationResults = simResult.nodes_results;
                // Try different key formats to get simulation data
                const nodeData = simulationResults[nodeIdStr] || 
                                 simulationResults[nodeId] ||
                                 (nodeIdNum !== null ? simulationResults[nodeIdNum] : undefined);

                if (nodeData && Array.isArray(nodeData) && nodeData.length > 0) {
                    const latestData = nodeData[nodeData.length - 1];
                    console.log('✅ Found simulation data directly:', latestData);
                    
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
                        console.log('⚠️ Base node not found, creating from simulation data only');
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
                } else {
                    console.log('❌ No simulation data found for node:', nodeIdStr);
                    console.log('Available keys in simulation results:', Object.keys(simulationResults).slice(0, 20));
                }
            } else {
                console.log('❌ No simulation data available in Redux store');
            }
        }

        if (!nodeToShow) {
            console.error('❌ Could not find node data for:', nodeIdStr);
            // Try to find any node with this ID as fallback
            const fallbackNode = nodes.find(n => String(n.id) === nodeIdStr || String(n.id) === nodeId);
            if (fallbackNode) {
                nodeToShow = fallbackNode;
                console.log('Using fallback node (may not have simulation data)');
            }
        }

        if (nodeToShow) {
            console.log('Final node data to show:', {
                id: nodeToShow.id,
                pressure: nodeToShow.pressure,
                head: nodeToShow.head,
                demand: nodeToShow.demand,
                flow: nodeToShow.flow
            });

            setSelectedNodeData(nodeToShow);
            setTooltipVisible(true);
            if (clickEvent) {
                setTooltipPosition(clickEvent);
            }
        } else {
            console.error('❌ Cannot display tooltip: no node data available');
        }
        
        console.log('====================');
    };

    const handleTooltipClose = () => {
        setTooltipVisible(false);
        setSelectedNodeData(null);
    };

    const handlePipeClick = (pipeId: string, properties: any, clickEvent?: { x: number; y: number }) => {
        console.log('Pipe clicked:', { pipeId, properties, clickEvent });
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
            console.log('Updating Mapbox pipes layer with', pipes.length, 'pipes');
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
