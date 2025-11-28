import React, { useState } from 'react';
import { Button, Card, Space, Typography, Alert, Divider } from 'antd';
import { useSimulation } from '../../hooks/useApi';
import { SimulationParams } from '../../services/types';

const { Title, Text, Paragraph } = Typography;

const SimulationDebug: React.FC = () => {
    const { data, loading, error, runSimulation } = useSimulation();
    const [testResults, setTestResults] = useState<any>(null);

    const testSimulation = async () => {
        console.log('Testing simulation...');

        const params: SimulationParams = {
            station_codes: ['13085'], // Use correct station code from mapping
            hours_back: 24,
            duration: 24,
            hydraulic_timestep: 1,
            report_timestep: 1
        };

        try {
            runSimulation(params);
            setTestResults({ status: 'started', params });
        } catch (err) {
            console.error('Simulation test failed:', err);
            setTestResults({ status: 'error', error: err });
        }
    };

    const clearResults = () => {
        setTestResults(null);
    };

    return (
        <Card title="🔧 Simulation Debug Panel" style={{ margin: '16px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                    <Button
                        type="primary"
                        onClick={testSimulation}
                        loading={loading}
                        style={{ marginRight: '8px' }}
                    >
                        Test Simulation
                    </Button>
                    <Button onClick={clearResults}>
                        Clear Results
                    </Button>
                </div>

                <Divider />

                {/* Current Status */}
                <div>
                    <Title level={5}>Current Status:</Title>
                    <Space direction="vertical">
                        <Text>Loading: {loading ? 'Yes' : 'No'}</Text>
                        <Text>Has Data: {data ? 'Yes' : 'No'}</Text>
                        <Text>Success: {data?.success ? 'Yes' : 'No'}</Text>
                        <Text>Error: {error || 'None'}</Text>
                    </Space>
                </div>

                {/* Test Results */}
                {testResults && (
                    <div>
                        <Title level={5}>Test Results:</Title>
                        <Alert
                            message={testResults.status === 'started' ? 'Simulation Started' : 'Error'}
                            type={testResults.status === 'started' ? 'info' : 'error'}
                            description={
                                testResults.status === 'started'
                                    ? `Testing with params: ${JSON.stringify(testResults.params, null, 2)}`
                                    : testResults.error?.toString()
                            }
                        />
                    </div>
                )}

                {/* Simulation Data */}
                {data && (
                    <div>
                        <Title level={5}>Simulation Data:</Title>
                        <Card size="small" style={{ backgroundColor: '#f5f5f5' }}>
                            <pre style={{ fontSize: '12px', maxHeight: '300px', overflow: 'auto' }}>
                                {JSON.stringify(data, null, 2)}
                            </pre>
                        </Card>
                    </div>
                )}

                {/* Error Display */}
                {error && (
                    <Alert
                        message="Error"
                        description={error}
                        type="error"
                        showIcon
                    />
                )}
            </Space>
        </Card>
    );
};

export default SimulationDebug;
