import React from 'react';
import { Card } from 'antd';

interface PipeTooltipProps {
    pipeId: string | null;
    properties: any;
    visible: boolean;
    onClose: () => void;
    position?: { x: number; y: number };
}

const PipeTooltip: React.FC<PipeTooltipProps> = ({
    pipeId,
    properties,
    visible,
    onClose,
    position
}) => {
    // Early return without logging if not visible (avoids console noise)
    if (!visible || !pipeId || !properties) {
        return null;
    }

    const flow = properties.flow || 0;
    const velocity = properties.velocity || 0;
    const headloss = properties.headloss || 0;

    // Only log when actually rendering with data
    console.log('PipeTooltip rendering:', {
        pipeId,
        flow,
        velocity,
        headloss,
        from_node: properties.from_node,
        to_node: properties.to_node
    });

    return (
        <div
            style={{
                position: 'absolute',
                left: position ? `${position.x + 10}px` : '50%',
                top: position ? `${position.y + 10}px` : '50%',
                transform: position ? 'none' : 'translate(-50%, -50%)',
                zIndex: 1000,
                pointerEvents: 'auto'
            }}
        >
            <Card
                title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>Pipe: {pipeId}</span>
                        <button
                            onClick={onClose}
                            style={{
                                background: 'none',
                                border: 'none',
                                fontSize: '18px',
                                cursor: 'pointer',
                                padding: '0 8px'
                            }}
                        >
                            ×
                        </button>
                    </div>
                }
                style={{
                    width: 300,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                }}
                size="small"
            >
                <div style={{ fontSize: '14px' }}>
                    <div style={{ marginBottom: '8px' }}>
                        <strong>From:</strong> {properties.from_node}
                    </div>
                    <div style={{ marginBottom: '8px' }}>
                        <strong>To:</strong> {properties.to_node}
                    </div>
                    <div style={{
                        padding: '8px',
                        background: '#f5f5f5',
                        borderRadius: '4px',
                        marginBottom: '4px'
                    }}>
                        <strong>Flow:</strong>{' '}
                        <span style={{
                            color: Math.abs(flow) > 0.5 ? '#f44336' :
                                Math.abs(flow) > 0.2 ? '#ff9800' :
                                    '#4caf50'
                        }}>
                            {flow.toFixed(4)} LPS
                        </span>
                        {flow < 0 && <span style={{ color: '#666', fontSize: '12px' }}> (reverse)</span>}
                    </div>
                    {velocity !== 0 && (
                        <div style={{ marginBottom: '4px' }}>
                            <strong>Velocity:</strong> {velocity.toFixed(4)} m/s
                        </div>
                    )}
                    {headloss !== 0 && (
                        <div style={{ marginBottom: '4px' }}>
                            <strong>Headloss:</strong> {headloss.toFixed(4)} m
                        </div>
                    )}
                </div>
            </Card>
        </div>
    );
};

export default PipeTooltip;

