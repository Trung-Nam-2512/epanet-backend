/**
 * Leak Alert Panel Component
 * Hiển thị danh sách leaks được phát hiện
 */
import React, { useState } from 'react';
import { Card, List, Tag, Typography, Empty, Spin, Alert, Statistic, Row, Col, Slider, Space, Button, Tooltip } from 'antd';
import { WarningOutlined, ExclamationCircleOutlined, ReloadOutlined, SettingOutlined, DownloadOutlined } from '@ant-design/icons';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { Leak } from '../services/leakDetection';
import { setThreshold, detectLeaksFromSimulation } from '../store/slices/leakDetectionSlice';
import { exportLeaksToExcel } from '../utils/exportExcel';

const { Text } = Typography;

interface LeakAlertPanelProps {
  onLeakClick?: (leak: Leak) => void;
}

export const LeakAlertPanel: React.FC<LeakAlertPanelProps> = ({ onLeakClick }) => {
  const dispatch = useDispatch<AppDispatch>();
  const { leaks, summary, isDetecting, isReady, error, threshold } = useSelector(
    (state: RootState) => state.leakDetection
  );
  const simulationResult = useSelector((state: RootState) => state.network.data?.simulation_result);
  
  const [localThreshold, setLocalThreshold] = useState<number>(threshold || 0.1);
  const [showThresholdControl, setShowThresholdControl] = useState(false);

  // Update local threshold when Redux threshold changes
  React.useEffect(() => {
    if (threshold !== null) {
      setLocalThreshold(threshold);
    }
  }, [threshold]);

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('vi-VN', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getProbabilityColor = (probability: number): string => {
    if (probability >= 0.8) return 'red';
    if (probability >= 0.6) return 'orange';
    return 'gold';
  };

  const getProbabilityLevel = (probability: number): string => {
    if (probability >= 0.8) return 'Cao';
    if (probability >= 0.6) return 'Trung bình';
    return 'Thấp';
  };

  const handleExportExcel = () => {
    if (leaks.length === 0) {
      return;
    }

    exportLeaksToExcel({
      leaks,
      summary: summary || null,
      threshold: threshold || 0.1,
      exportDate: new Date()
    });
  };

  // Loading state
  if (isDetecting) {
    return (
      <Card>
        <Spin tip="Đang phát hiện rò rỉ..." size="large" />
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card>
        <Alert
          message="Lỗi phát hiện rò rỉ"
          description={error}
          type="error"
          showIcon
          icon={<ExclamationCircleOutlined />}
        />
      </Card>
    );
  }

  // Service not ready
  if (!isReady) {
    return (
      <Card>
        <Alert
          message="Dịch vụ chưa sẵn sàng"
          description="Leak detection service đang không khả dụng. Vui lòng thử lại sau."
          type="warning"
          showIcon
        />
      </Card>
    );
  }

  return (
    <Card
      title={
        <span>
          <WarningOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
          Phát hiện rò rỉ
          {leaks.length > 0 && (
            <Tag color="red" style={{ marginLeft: 8 }}>
              {leaks.length}
            </Tag>
          )}
        </span>
      }
      style={{ marginBottom: 16 }}
      extra={
        <Space>
          {leaks.length > 0 && (
            <Tooltip title="Xuất báo cáo Excel">
              <Button
                icon={<DownloadOutlined />}
                size="small"
                type="primary"
                onClick={handleExportExcel}
              >
                Excel
              </Button>
            </Tooltip>
          )}
          {threshold && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              Ngưỡng: {(threshold * 100).toFixed(0)}%
            </Text>
          )}
          <Tooltip title="Điều chỉnh ngưỡng">
            <Button
              type="text"
              size="small"
              icon={<SettingOutlined />}
              onClick={() => setShowThresholdControl(!showThresholdControl)}
            />
          </Tooltip>
        </Space>
      }
    >
      {/* Threshold Control */}
      {showThresholdControl && (
        <Card
          size="small"
          style={{ marginBottom: 16, backgroundColor: '#fafafa' }}
          title={
            <Space>
              <SettingOutlined />
              <Text strong>Điều chỉnh ngưỡng phát hiện</Text>
            </Space>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Ngưỡng hiện tại: <Text strong>{(localThreshold * 100).toFixed(1)}%</Text>
              </Text>
            </div>
            <Slider
              min={0.01}
              max={0.5}
              step={0.01}
              value={localThreshold}
              onChange={(value) => setLocalThreshold(value)}
              tooltip={{ formatter: (value) => `${((value || 0) * 100).toFixed(1)}%` }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#999' }}>
              <span>1% (Nhạy cảm)</span>
              <span>25% (Cân bằng)</span>
              <span>50% (Chặt chẽ)</span>
            </div>
            <Space>
              <Button
                type="primary"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => {
                  dispatch(setThreshold(localThreshold));
                  // Re-detect với threshold mới nếu có simulation result
                  if (simulationResult) {
                    dispatch(detectLeaksFromSimulation({
                      simulationResult,
                      threshold: localThreshold
                    }));
                  }
                }}
                loading={isDetecting}
              >
                Áp dụng
              </Button>
              <Button
                size="small"
                onClick={() => {
                  setLocalThreshold(threshold || 0.1);
                  setShowThresholdControl(false);
                }}
              >
                Hủy
              </Button>
            </Space>
          </Space>
        </Card>
      )}

      {/* Summary Statistics */}
      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Statistic
              title="Tổng records"
              value={summary.total_records}
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="Phát hiện"
              value={summary.detected_leaks}
              valueStyle={{ fontSize: '14px', color: summary.detected_leaks > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="Tỷ lệ"
              value={(summary.detection_rate * 100).toFixed(2)}
              suffix="%"
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
        </Row>
      )}

      {/* Leaks List */}
      {leaks.length === 0 ? (
        <Empty 
          description="Không phát hiện rò rỉ" 
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          dataSource={leaks}
          size="small"
          style={{ maxHeight: '400px', overflowY: 'auto' }}
          renderItem={(leak: Leak, index: number) => (
            <List.Item
              key={`${leak.node_id}-${leak.timestamp}-${index}`}
              onClick={() => onLeakClick?.(leak)}
              style={{
                border: '1px solid #f0f0f0',
                borderRadius: '4px',
                marginBottom: '8px',
                padding: '12px',
                backgroundColor: '#fafafa',
                cursor: onLeakClick ? 'pointer' : 'default',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                if (onLeakClick) {
                  e.currentTarget.style.backgroundColor = '#f0f0f0';
                  e.currentTarget.style.transform = 'translateX(4px)';
                }
              }}
              onMouseLeave={(e) => {
                if (onLeakClick) {
                  e.currentTarget.style.backgroundColor = '#fafafa';
                  e.currentTarget.style.transform = 'translateX(0)';
                }
              }}
            >
              <List.Item.Meta
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Text strong style={{ fontSize: '14px' }}>
                        Node: {leak.node_id}
                      </Text>
                      <Tag 
                        color={getProbabilityColor(leak.probability)}
                        style={{ marginLeft: 8 }}
                      >
                        {(leak.probability * 100).toFixed(1)}% ({getProbabilityLevel(leak.probability)})
                      </Tag>
                    </div>
                  </div>
                }
                description={
                  <div style={{ marginTop: 8 }}>
                    <div style={{ marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        <strong>Thời gian:</strong> {formatTime(leak.timestamp)}
                      </Text>
                    </div>
                    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        <strong>Pressure:</strong> {leak.pressure.toFixed(2)} m
                      </Text>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        <strong>Head:</strong> {leak.head.toFixed(2)} m
                      </Text>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        <strong>Demand:</strong> {leak.demand.toFixed(3)} m³/s
                      </Text>
                    </div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
};

