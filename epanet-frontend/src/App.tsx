import React from 'react';
import { Provider } from 'react-redux';
import { ConfigProvider } from 'antd';
import { store } from './store';
import AppLayout from './components/layout/AppLayout';
import 'antd/dist/reset.css';
import './App.css';

const App: React.FC = () => {
    return (
        <Provider store={store}>
            <ConfigProvider
                theme={{
                    token: {
                        colorPrimary: '#1976d2',
                        colorSuccess: '#52c41a',
                        colorWarning: '#faad14',
                        colorError: '#ff4d4f',
                        colorInfo: '#1890ff',
                    },
                }}
            >
                <AppLayout />
            </ConfigProvider>
        </Provider>
    );
};

export default App;

