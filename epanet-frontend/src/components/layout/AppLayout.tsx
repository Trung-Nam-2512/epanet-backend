import React, { useState } from 'react';
import { Layout } from 'antd';
import Sidebar from './Sidebar';
import MapContainer from '../map/MapContainer';

const { Sider, Content } = Layout;

interface NavigationState {
    targetNodeId: string | null;
    shouldZoom: boolean;
    shouldHighlight: boolean;
}

const AppLayout: React.FC = () => {
    const [navigationState, setNavigationState] = useState<NavigationState>({
        targetNodeId: null,
        shouldZoom: false,
        shouldHighlight: false,
    });

    const handleNavigateToNode = (nodeId: string) => {
        setNavigationState({
            targetNodeId: nodeId,
            shouldZoom: true,
            shouldHighlight: true,
        });
    };

    const handleNavigationComplete = () => {
        setNavigationState({
            targetNodeId: null,
            shouldZoom: false,
            shouldHighlight: false,
        });
    };

    return (
        <Layout style={{ height: '100vh' }}>
            <Sider
                width={300}
                theme="dark"
                style={{
                    background: '#001529',
                    borderRight: '1px solid #f0f0f0'
                }}
            >
                <Sidebar onNavigateToNode={handleNavigateToNode} />
            </Sider>
            <Layout>
                <Content style={{ margin: 0, padding: 0 }}>
                    <MapContainer
                        navigationState={navigationState}
                        onNavigationComplete={handleNavigationComplete}
                    />
                </Content>
            </Layout>
        </Layout>
    );
};

export default AppLayout;

