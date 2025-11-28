import React from 'react';
import { Card, Typography, Space, Tag, Divider, Alert } from 'antd';
import {
    EnvironmentOutlined,
    ThunderboltOutlined,
    DropboxOutlined,
    InfoCircleOutlined,
    WarningOutlined
} from '@ant-design/icons';
import { useSelector } from 'react-redux';
import { NetworkNode } from '../../services/types';
import { RootState } from '../../store';

const { Title, Text } = Typography;

interface NodeTooltipProps {
    node: NetworkNode | null;
    visible: boolean;
    onClose: () => void;
    position?: { x: number; y: number };
}

const NodeTooltip: React.FC<NodeTooltipProps> = ({ node, visible, onClose, position }) => {
    // Get leaks from Redux store (MUST be called before early return)
    const leaks = useSelector((state: RootState) => state.leakDetection.leaks);
    
    if (!visible || !node) return null;

    // Find leak for current node (try multiple ID formats)
    const nodeIdStr = String(node.id);
    const leak = leaks.find(l => {
        const leakNodeId = String(l.node_id);
        return leakNodeId === nodeIdStr || leakNodeId === node.id;
    });

    // Debug log - consolidated into single log
    console.log('NodeTooltip rendering:', {
        id: node.id,
        pressure: node.pressure,
        head: node.head,
        demand: node.demand,
        flow: node.flow,
        coordinates: node.coordinates,
        hasLeak: !!leak
    });

    const getPressureStatus = (pressure: number) => {
        if (pressure > 30) return { color: 'success', text: 'Excellent' };
        if (pressure > 20) return { color: 'warning', text: 'Good' };
        if (pressure > 10) return { color: 'error', text: 'Low' };
        return { color: 'default', text: 'Critical' };
    };

    const getFlowStatus = (flow: number) => {
        const absFlow = Math.abs(flow);
        if (absFlow > 50) return { color: 'success', text: 'High Flow' };
        if (absFlow > 20) return { color: 'warning', text: 'Medium Flow' };
        if (absFlow > 5) return { color: 'processing', text: 'Low Flow' };
        return { color: 'default', text: 'No Flow' };
    };

    const pressureStatus = getPressureStatus(node.pressure || 0);
    const flowStatus = getFlowStatus(node.flow || 0);

    return (
        <div
            className="node-tooltip"
            style={{
                position: 'absolute',
                left: position ? `${position.x}px` : '20px',
                top: position ? `${position.y - 10}px` : '20px',
                zIndex: 1000,
                maxWidth: '350px',
                transform: position ? 'translate(-50%, -100%)' : 'none'
            }}
        >
            <Card
                size="small"
                title={
                    <Space>
                        <EnvironmentOutlined style={{ color: '#1890ff' }} />
                        <Text strong>Node {node.id}</Text>
                    </Space>
                }
                extra={
                    <Text
                        type="secondary"
                        style={{ cursor: 'pointer' }}
                        onClick={onClose}
                    >
                        ✕
                    </Text>
                }
                style={{
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    borderRadius: '8px',
                    border: '1px solid #d9d9d9'
                }}
            >
                {/* Leak Alert */}
                {leak && (
                    <Alert
                        message={`⚠️ Phát hiện rò rỉ: ${(leak.probability * 100).toFixed(1)}%`}
                        description={`Xác suất rò rỉ: ${leak.probability >= 0.8 ? 'Cao' : leak.probability >= 0.6 ? 'Trung bình' : 'Thấp'}`}
                        type="warning"
                        showIcon
                        icon={<WarningOutlined />}
                        style={{ marginBottom: 12 }}
                    />
                )}

                {/* Status Indicators */}
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Space>
                        <Tag color={pressureStatus.color} icon={<ThunderboltOutlined />}>
                            Pressure: {(node.pressure || 0).toFixed(2)}m
                        </Tag>
                        <Tag color={flowStatus.color} icon={<DropboxOutlined />}>
                            Flow: {(node.flow || 0).toFixed(2)}L/s
                        </Tag>
                    </Space>

                    <Divider style={{ margin: '8px 0' }} />

                    {/* Detailed Information */}
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text type="secondary">Head:</Text>
                            <Text strong>{(node.head || 0).toFixed(2)}m</Text>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text type="secondary">Demand:</Text>
                            <Text strong>{(node.demand || 0).toFixed(2)}L/s</Text>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text type="secondary">Coordinates:</Text>
                            <Text code>
                                {node.coordinates.lat.toFixed(6)}, {node.coordinates.lng.toFixed(6)}
                            </Text>
                        </div>
                    </Space>

                    <Divider style={{ margin: '8px 0' }} />

                    {/* Status Summary */}
                    <div style={{ textAlign: 'center' }}>
                        <Space>
                            <InfoCircleOutlined style={{ color: '#1890ff' }} />
                            <Text type="secondary">
                                Status: {pressureStatus.text} | {flowStatus.text}
                            </Text>
                        </Space>
                    </div>
                </Space>
            </Card>

        </div>
    );
};

export default NodeTooltip;
