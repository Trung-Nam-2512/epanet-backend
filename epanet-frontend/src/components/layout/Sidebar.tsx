import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Alert, Spin, Typography, Row, Col, Statistic, InputNumber, Switch, Input, Divider } from 'antd';
import { PlayCircleOutlined, SettingOutlined, ThunderboltOutlined, DatabaseOutlined, ClockCircleOutlined, InfoCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useSimulation } from '../../hooks/useApi';
import { SimulationParams, NetworkNode } from '../../services/types';
import { generateNetworkLayout } from '../../services/networkData';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '../../store';
import { detectLeaksFromSimulation, checkLeakDetectionStatus } from '../../store/slices/leakDetectionSlice';
import { LeakAlertPanel } from '../LeakAlertPanel';
import { NodeSearch } from '../NodeSearch';

const { Group } = Input;

const { Title, Text } = Typography;

interface SidebarProps {
    onNavigateToNode?: (nodeId: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onNavigateToNode }) => {
    const [form] = Form.useForm();
    const { data, loading, error, runSimulation, selectNode } = useSimulation();
    const [isSimulating, setIsSimulating] = useState(false);
    const [nodes, setNodes] = useState<NetworkNode[]>([]);
    const [autoRefresh, setAutoRefresh] = useState(false);
    
    // Redux for leak detection
    const dispatch = useDispatch<AppDispatch>();
    const leakDetection = useSelector((state: RootState) => state.leakDetection);

    // Load network data once
    useEffect(() => {
        const loadNetworkData = async () => {
            try {
                const { nodes: networkNodes } = await generateNetworkLayout();
                setNodes(networkNodes);
            } catch (error) {
                console.error('Error loading network data:', error);
            }
        };
        loadNetworkData();
    }, []); // Only run once

    // Check leak detection service status on mount
    useEffect(() => {
        console.log('Checking leak detection service status...');
        dispatch(checkLeakDetectionStatus()).then((result: any) => {
            console.log('Leak detection status check result:', result);
            if (result.payload) {
                console.log('Service ready:', result.payload.ready);
                console.log('Service message:', result.payload.message);
            }
        }).catch((error: any) => {
            console.error('Error checking leak detection status:', error);
        });
    }, [dispatch]);

    // Detect leaks when simulation completes
    useEffect(() => {
        if (data && data.success && data.simulation_result && !loading) {
            // Convert simulation result to format expected by leak detection API
            const simulationResultForLeakDetection = {
                run_id: data.simulation_result.run_id,
                status: data.simulation_result.status,
                timestamp: data.simulation_result.timestamp,
                duration: data.simulation_result.duration,
                nodes_results: data.simulation_result.nodes_results,
                pipes_results: data.simulation_result.pipes_results,
                pumps_results: data.simulation_result.pumps_results,
            };
            
            // Only detect if service is ready
            if (leakDetection.isReady) {
                console.log('Service is ready, detecting leaks from simulation...');
                dispatch(detectLeaksFromSimulation({
                    simulationResult: simulationResultForLeakDetection,
                    threshold: leakDetection.threshold || undefined
                }))
                    .then((result: any) => {
                        console.log('Leak detection result:', result);
                        if (result.payload) {
                            console.log('Leaks detected:', result.payload.leaks?.length || 0);
                            console.log('Summary:', result.payload.summary);
                        }
                    })
                    .catch((error: any) => {
                        console.error('Error detecting leaks:', error);
                    });
            } else {
                console.warn('Leak detection service not ready. isReady:', leakDetection.isReady);
                console.warn('Error:', leakDetection.error);
            }
        }
    }, [data, loading, dispatch, leakDetection.isReady]);

    // Set default values cho form
    React.useEffect(() => {
        form.setFieldsValue({
            station_codes: ['13085'],  // Fixed station code
            hours_back: 24,              // Get SCADA data from last 24 hours
            duration: 1,                  // Run simulation for 1 hour (realtime)
            hydraulic_timestep: 1,
            report_timestep: 1
        });
    }, [form]);

    // Update nodes when simulation data changes
    useEffect(() => {
        if (data && data.success && data.simulation_result && nodes.length > 0) {
            // Check if data has actually changed to avoid infinite loop
            const updatedNodes = nodes.map(node => {
                const nodeData = data.simulation_result.nodes_results[node.id];
                if (nodeData && nodeData.length > 0) {
                    const latestData = nodeData[nodeData.length - 1];
                    return {
                        ...node,
                        pressure: latestData.pressure || 0,
                        head: latestData.head || 0,
                        demand: latestData.demand || 0,
                        flow: latestData.flow || 0,
                    };
                }
                return node;
            });

            // Only update if data actually changed
            const hasChanged = updatedNodes.some((node, index) => {
                const oldNode = nodes[index];
                return node.pressure !== oldNode.pressure ||
                    node.head !== oldNode.head ||
                    node.demand !== oldNode.demand ||
                    node.flow !== oldNode.flow;
            });

            if (hasChanged) {
                setNodes(updatedNodes);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [data]); // Only depend on data, not nodes (to avoid infinite loop)

    const handleSimulation = async (values: SimulationParams) => {
        setIsSimulating(true);
        try {
            await runSimulation(values);
        } finally {
            setIsSimulating(false);
        }
    };

    const handleNodeClick = (nodeId: string) => {
        selectNode(nodeId);
    };

    const handleNavigateToNode = (nodeId: string) => {
        // Select node for highlighting
        selectNode(nodeId);

        // Navigate to node on map if callback is provided
        if (onNavigateToNode) {
            onNavigateToNode(nodeId);
        }

        // Scroll to top to show simulation results
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    return (
        <div style={{
            padding: '20px',
            height: '100%',
            overflowY: 'auto',
            background: 'linear-gradient(180deg, #0a1929 0%, #001529 50%, #0a1929 100%)',
            position: 'relative'
        }}>
            {/* Header Section */}
            <div style={{
                textAlign: 'center',
                marginBottom: '24px',
                padding: '20px 16px',
                background: 'linear-gradient(135deg, rgba(24, 144, 255, 0.15) 0%, rgba(64, 169, 255, 0.08) 100%)',
                borderRadius: '16px',
                border: '1px solid rgba(24, 144, 255, 0.2)',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '10px'
                }}>
                    <ThunderboltOutlined style={{
                        fontSize: '28px',
                        color: '#40a9ff',
                        marginRight: '10px'
                    }} />
                    <Title level={3} style={{
                        color: '#e6f7ff',
                        margin: 0,
                        fontWeight: 'bold'
                    }}>
                        HỆ THỐNG QUẢN LÝ RÒ RỈ
                    </Title>
                </div>
                <Text style={{
                    color: '#91d5ff',
                    fontSize: '13px',
                    fontWeight: '500',
                    letterSpacing: '0.5px'
                }}>
                    Water Leakage Management System
                </Text>
            </div>

            {/* Node Search */}
            <Card
                style={{
                    marginBottom: '20px',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(24, 144, 255, 0.3)',
                    borderRadius: '14px',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.12)'
                }}
                bodyStyle={{ padding: '18px' }}
            >
                <div style={{ marginBottom: '10px' }}>
                    <Text style={{ color: '#91d5ff', fontWeight: '600', fontSize: '13px' }}>
                        Tìm kiếm Node
                    </Text>
                </div>
                <NodeSearch 
                    onNodeSelect={(nodeId) => {
                        if (onNavigateToNode) {
                            onNavigateToNode(nodeId);
                        }
                    }}
                />
            </Card>

            {/* Station Info Card */}
            <Card
                style={{
                    marginBottom: '20px',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(82, 196, 26, 0.3)',
                    borderRadius: '14px',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.12)'
                }}
                bodyStyle={{ padding: '18px' }}
            >
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '14px' }}>
                    <DatabaseOutlined style={{
                        fontSize: '18px',
                        color: '#73d13d',
                        marginRight: '10px'
                    }} />
                    <Text style={{ color: '#b7eb8f', fontWeight: '600', fontSize: '13px' }}>SCADA Station</Text>
                </div>
                <div style={{
                    background: 'linear-gradient(135deg, rgba(82, 196, 26, 0.15) 0%, rgba(115, 209, 61, 0.08) 100%)',
                    padding: '14px',
                    borderRadius: '10px',
                    border: '1px solid rgba(82, 196, 26, 0.3)'
                }}>
                    <Text style={{
                        color: '#95de64',
                        fontSize: '18px',
                        fontWeight: 'bold',
                        fontFamily: 'monospace',
                        letterSpacing: '2px'
                    }}>
                        13085
                    </Text>
                    <div style={{ marginTop: '6px' }}>
                        <Text style={{ color: '#d9f7be', fontSize: '12px', fontWeight: '500' }}>
                            Main Pump Station - Boundary Condition
                        </Text>
                    </div>
                </div>
            </Card>

            {/* Simulation Control */}
            <Card
                style={{
                    marginBottom: '20px',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(114, 46, 209, 0.25)',
                    borderRadius: '14px',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.12)'
                }}
                title={
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <SettingOutlined style={{
                            fontSize: '18px',
                            color: '#b37feb',
                            marginRight: '10px'
                        }} />
                        <Text style={{ color: '#f9f0ff', fontWeight: '600', fontSize: '14px' }}>Simulation Control</Text>
                    </div>
                }
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSimulation}
                    size="small"
                >
                    {/* Hidden station_codes field */}
                    <Form.Item name="station_codes" style={{ display: 'none' }}>
                        <Input type="hidden" />
                    </Form.Item>

                    {/* Time Configuration */}
                    <div style={{ marginBottom: '18px' }}>
                        <Text style={{ color: '#d3adf7', fontSize: '11px', fontWeight: '600', letterSpacing: '1px' }}>
                            TIME CONFIGURATION
                        </Text>
                        <Row gutter={8}>
                            <Col span={12}>
                                <Form.Item
                                    name="hours_back"
                                    label={<Text style={{ color: 'white', fontSize: '12px' }}>SCADA Data</Text>}
                                >
                                    <InputNumber
                                        style={{
                                            width: '100%',
                                            backgroundColor: '#ffffff'
                                        }}
                                        min={1}
                                        max={168}
                                        placeholder="24"
                                        disabled={true}
                                        controls={{
                                            upIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▲</div>,
                                            downIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▼</div>
                                        }}
                                    />
                                </Form.Item>
                                <Text style={{ color: '#8c8c8c', fontSize: '10px', marginTop: '-8px', display: 'block', marginBottom: '8px' }}>
                                    Get data from last 24 hours
                                </Text>
                            </Col>
                            <Col span={12}>
                                <Form.Item
                                    name="duration"
                                    label={<Text style={{ color: 'white', fontSize: '12px' }}>Simulation</Text>}
                                >
                                    <InputNumber
                                        style={{
                                            width: '100%',
                                            backgroundColor: '#ffffff'
                                        }}
                                        min={1}
                                        max={168}
                                        placeholder="1"
                                        disabled={true}
                                        controls={{
                                            upIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▲</div>,
                                            downIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▼</div>
                                        }}
                                    />
                                </Form.Item>
                                <Text style={{ color: '#8c8c8c', fontSize: '10px', marginTop: '-8px', display: 'block', marginBottom: '8px' }}>
                                    Run for 1 hour
                                </Text>
                            </Col>
                        </Row>
                    </div>

                    {/* Advanced Settings */}
                    <div style={{ marginBottom: '18px' }}>
                        <Text style={{ color: '#d3adf7', fontSize: '11px', fontWeight: '600', letterSpacing: '1px' }}>
                            ADVANCED SETTINGS
                        </Text>
                        <Row gutter={8}>
                            <Col span={12}>
                                <Form.Item
                                    name="hydraulic_timestep"
                                    label={<Text style={{ color: 'white', fontSize: '12px' }}>Hydraulic Step</Text>}
                                >
                                    <InputNumber
                                        style={{
                                            width: '100%',
                                            backgroundColor: '#ffffff'
                                        }}
                                        min={0.25}
                                        max={24}
                                        step={0.25}
                                        placeholder="1"
                                        disabled={true}
                                        controls={{
                                            upIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▲</div>,
                                            downIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▼</div>
                                        }}
                                    />
                                </Form.Item>
                                <Text style={{ color: '#8c8c8c', fontSize: '10px', marginTop: '-8px', display: 'block', marginBottom: '8px' }}>
                                    Default: 1h
                                </Text>
                            </Col>
                            <Col span={12}>
                                <Form.Item
                                    name="report_timestep"
                                    label={<Text style={{ color: 'white', fontSize: '12px' }}>Report Step</Text>}
                                >
                                    <InputNumber
                                        style={{
                                            width: '100%',
                                            backgroundColor: '#ffffff'
                                        }}
                                        min={0.25}
                                        max={24}
                                        step={0.25}
                                        placeholder="1"
                                        disabled={true}
                                        controls={{
                                            upIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▲</div>,
                                            downIcon: <div style={{ color: '#1890ff', fontSize: '10px' }}>▼</div>
                                        }}
                                    />
                                </Form.Item>
                                <Text style={{ color: '#8c8c8c', fontSize: '10px', marginTop: '-8px', display: 'block', marginBottom: '8px' }}>
                                    Default: 1h
                                </Text>
                            </Col>
                        </Row>
                    </div>

                    {/* Auto Refresh Toggle */}
                    <div style={{
                        marginBottom: '20px',
                        padding: '14px',
                        background: 'linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(64, 169, 255, 0.05) 100%)',
                        borderRadius: '10px',
                        border: '1px solid rgba(24, 144, 255, 0.2)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                <ClockCircleOutlined style={{
                                    fontSize: '16px',
                                    color: '#69c0ff',
                                    marginRight: '10px'
                                }} />
                                <Text style={{ color: '#e6f7ff', fontSize: '13px', fontWeight: '500' }}>Auto Refresh</Text>
                            </div>
                            <Switch
                                size="small"
                                checked={autoRefresh}
                                onChange={setAutoRefresh}
                            />
                        </div>
                    </div>

                    {/* Run Button */}
                    <Form.Item style={{ marginBottom: 0 }}>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading || isSimulating}
                            icon={<PlayCircleOutlined />}
                            block
                            size="large"
                            style={{
                                height: '44px',
                                background: 'linear-gradient(135deg, #722ed1 0%, #9254de 50%, #b37feb 100%)',
                                border: 'none',
                                borderRadius: '10px',
                                fontWeight: '700',
                                fontSize: '15px',
                                boxShadow: '0 4px 12px rgba(114, 46, 209, 0.3)',
                                transition: 'all 0.3s ease'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.boxShadow = '0 6px 16px rgba(114, 46, 209, 0.4)';
                                e.currentTarget.style.transform = 'translateY(-1px)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(114, 46, 209, 0.3)';
                                e.currentTarget.style.transform = 'translateY(0)';
                            }}
                        >
                            {loading || isSimulating ? 'Running Simulation...' : '▶ Run Simulation'}
                        </Button>
                    </Form.Item>
                </Form>
            </Card>

            {/* Results Section */}
            {data && (
                <Card
                    style={{
                        marginBottom: '20px',
                        background: data.success ?
                            'linear-gradient(135deg, rgba(82, 196, 26, 0.15) 0%, rgba(115, 209, 61, 0.08) 100%)' :
                            'linear-gradient(135deg, rgba(255, 77, 79, 0.15) 0%, rgba(255, 114, 117, 0.08) 100%)',
                        border: data.success ?
                            '1px solid rgba(82, 196, 26, 0.4)' :
                            '1px solid rgba(255, 77, 79, 0.4)',
                        borderRadius: '14px',
                        boxShadow: data.success ?
                            '0 4px 12px rgba(82, 196, 26, 0.15)' :
                            '0 4px 12px rgba(255, 77, 79, 0.15)'
                    }}
                    title={
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                            {data.success ? (
                                <CheckCircleOutlined style={{
                                    fontSize: '18px',
                                    color: '#73d13d',
                                    marginRight: '10px'
                                }} />
                            ) : (
                                <InfoCircleOutlined style={{
                                    fontSize: '18px',
                                    color: '#ff7875',
                                    marginRight: '10px'
                                }} />
                            )}
                            <Text style={{
                                color: 'white',
                                fontWeight: '600',
                                fontSize: '14px'
                            }}>
                                Simulation Results
                            </Text>
                        </div>
                    }
                >
                    <Row gutter={16}>
                        <Col span={8}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c', fontSize: '11px' }}>Status</Text>}
                                value={data.success ? 'Success' : 'Failed'}
                                valueStyle={{
                                    color: data.success ? '#52c41a' : '#ff4d4f',
                                    fontSize: '14px',
                                    fontWeight: 'bold'
                                }}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c', fontSize: '11px' }}>Nodes</Text>}
                                value={Object.keys(data.simulation_result?.nodes_results || {}).length}
                                valueStyle={{
                                    color: '#1890ff',
                                    fontSize: '14px',
                                    fontWeight: 'bold'
                                }}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title={<Text style={{ color: '#8c8c8c', fontSize: '11px' }}>Duration</Text>}
                                value={`${data.simulation_result?.duration || 0}h`}
                                valueStyle={{
                                    color: '#722ed1',
                                    fontSize: '14px',
                                    fontWeight: 'bold'
                                }}
                            />
                        </Col>
                    </Row>
                </Card>
            )}

            {/* Leak Detection Panel - Always show to display status */}
            <div style={{ marginBottom: '20px' }}>
                <LeakAlertPanel 
                    onLeakClick={(leak) => {
                        // Navigate to node on map
                        if (onNavigateToNode) {
                            onNavigateToNode(leak.node_id);
                        }
                    }}
                />
            </div>

            {/* Error Display */}
            {error && (
                <Alert
                    message="Simulation Error"
                    description={error}
                    type="error"
                    showIcon
                    style={{
                        marginBottom: '20px',
                        borderRadius: '8px'
                    }}
                />
            )}

            {/* Loading State */}
            {loading && (
                <div style={{
                    textAlign: 'center',
                    padding: '40px 20px',
                    background: 'rgba(255, 255, 255, 0.03)',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.1)'
                }}>
                    <Spin size="large" />
                    <div style={{
                        marginTop: '16px',
                        color: 'white',
                        fontSize: '14px',
                        fontWeight: '500'
                    }}>
                        Running simulation...
                    </div>
                </div>
            )}

        </div>
    );
};

export default Sidebar;