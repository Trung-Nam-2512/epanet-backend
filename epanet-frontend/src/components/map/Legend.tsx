import React, { useState } from 'react';
import { Card, Table, Tag, Typography } from 'antd';
import { UpOutlined, DownOutlined, InfoCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

const Legend: React.FC = () => {
    const [collapsed, setCollapsed] = useState(false);

    // Bảng ngưỡng Demand Ratio
    const demandThresholds = [
        {
            key: '1',
            ratio: '> 150%',
            color: '#d32f2f',
            label: 'Đỏ đậm',
            status: 'Cảnh báo',
            description: 'Demand quá cao - Có thể có rò rỉ lớn, sự cố nghiêm trọng',
            severity: 'danger'
        },
        {
            key: '2',
            ratio: '> 120%',
            color: '#ff5722',
            label: 'Cam/Đỏ',
            status: 'Chú ý',
            description: 'Demand cao - Có thể có rò rỉ nhỏ hoặc nhu cầu tăng',
            severity: 'warning'
        },
        {
            key: '3',
            ratio: '80-120%',
            color: '#4caf50',
            label: 'Xanh lá',
            status: 'Bình thường',
            description: 'Demand ở mức bình thường - Hệ thống hoạt động ổn định',
            severity: 'success'
        },
        {
            key: '4',
            ratio: '50-80%',
            color: '#2196f3',
            label: 'Xanh dương',
            status: 'Chú ý',
            description: 'Demand thấp - Có thể do giờ thấp điểm hoặc cần kiểm tra',
            severity: 'info'
        },
        {
            key: '5',
            ratio: '0-50%',
            color: '#cddc39',
            label: 'Xanh vàng',
            status: 'Chú ý',
            description: 'Demand rất thấp - Có thể có vấn đề (van đóng, đường ống tắc)',
            severity: 'warning'
        }
    ];

    const columns = [
        {
            title: 'Màu',
            dataIndex: 'color',
            key: 'color',
            width: 60,
            render: (color: string) => (
                <div
                    style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        backgroundColor: color,
                        border: '2px solid #fff',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                    }}
                />
            ),
        },
        {
            title: 'Tỷ lệ',
            dataIndex: 'ratio',
            key: 'ratio',
            width: 80,
            render: (ratio: string) => (
                <Text strong style={{ fontSize: '12px' }}>{ratio}</Text>
            ),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status: string, record: any) => {
                const colorMap: Record<string, string> = {
                    'Bình thường': 'success',
                    'Chú ý': 'warning',
                    'Cảnh báo': 'error'
                };
                return (
                    <Tag color={colorMap[status] || 'default'} style={{ fontSize: '11px' }}>
                        {status}
                    </Tag>
                );
            },
        },
    ];

    return (
        <div
            style={{
                position: 'absolute',
                bottom: '20px',
                right: '20px',
                zIndex: 1000,
                pointerEvents: 'auto'
            }}
        >
            <Card
                title={
                    <div
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            cursor: 'pointer'
                        }}
                        onClick={() => setCollapsed(!collapsed)}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <InfoCircleOutlined style={{ color: '#1890ff' }} />
                            <span style={{ fontWeight: 'bold' }}>Ngưỡng Demand Ratio</span>
                        </div>
                        {collapsed ? <DownOutlined /> : <UpOutlined />}
                    </div>
                }
                style={{
                    width: 380,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    maxHeight: '85vh',
                    overflow: 'auto',
                    borderRadius: '8px'
                }}
                size="small"
                bodyStyle={{ display: collapsed ? 'none' : 'block', padding: '12px' }}
            >


                <Table
                    dataSource={demandThresholds}
                    columns={columns}
                    pagination={false}
                    size="small"
                    bordered={false}
                    showHeader={true}
                    rowKey="key"
                    style={{ fontSize: '12px' }}
                />
            </Card>
        </div>
    );
};

export default Legend;

