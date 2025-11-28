/**
 * Node Search Component
 * Tìm kiếm node và điều hướng đến node đó trên bản đồ
 */
import React, { useState, useEffect, useMemo } from 'react';
import { Input, AutoComplete, Card, Typography, Empty } from 'antd';
import { SearchOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { generateNetworkLayout } from '../services/networkData';
import { NetworkNode } from '../services/types';

const { Text } = Typography;

interface NodeSearchProps {
  onNodeSelect?: (nodeId: string) => void;
  placeholder?: string;
}

export const NodeSearch: React.FC<NodeSearchProps> = ({ 
  onNodeSelect,
  placeholder = "Tìm kiếm node (ví dụ: 322, 767, TXU2...)" 
}) => {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [searchValue, setSearchValue] = useState<string>('');
  const [options, setOptions] = useState<Array<{ value: string; label: React.ReactNode }>>([]);

  // Load nodes data
  useEffect(() => {
    const loadNodes = async () => {
      try {
        const { nodes: networkNodes } = await generateNetworkLayout();
        setNodes(networkNodes);
      } catch (error) {
        console.error('Error loading nodes for search:', error);
      }
    };
    loadNodes();
  }, []);

  // Filter nodes based on search value
  const filteredNodes = useMemo(() => {
    if (!searchValue || searchValue.trim() === '') {
      return [];
    }

    const searchLower = searchValue.toLowerCase().trim();
    return nodes.filter(node => 
      node.id.toLowerCase().includes(searchLower)
    ).slice(0, 10); // Limit to 10 results
  }, [nodes, searchValue]);

  // Update options when filtered nodes change
  useEffect(() => {
    const newOptions = filteredNodes.map(node => ({
      value: node.id,
      label: (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <EnvironmentOutlined style={{ color: '#1890ff' }} />
          <div>
            <Text strong>Node {node.id}</Text>
            {node.coordinates && (
              <div style={{ fontSize: '12px', color: '#999' }}>
                {node.coordinates.lat.toFixed(6)}, {node.coordinates.lng.toFixed(6)}
              </div>
            )}
          </div>
        </div>
      )
    }));

    setOptions(newOptions);
  }, [filteredNodes]);

  const handleSelect = (value: string) => {
    setSearchValue(value);
    if (onNodeSelect) {
      onNodeSelect(value);
    }
  };

  const handleSearch = (value: string) => {
    setSearchValue(value);
    
    // If exact match, trigger selection
    const exactMatch = nodes.find(node => 
      node.id.toLowerCase() === value.toLowerCase()
    );
    
    if (exactMatch && onNodeSelect) {
      onNodeSelect(exactMatch.id);
    }
  };

  return (
    <AutoComplete
      style={{ width: '100%' }}
      options={options}
      onSelect={handleSelect}
      onSearch={handleSearch}
      value={searchValue}
      placeholder={placeholder}
      allowClear
      filterOption={false} // We handle filtering manually
      notFoundContent={
        searchValue && filteredNodes.length === 0 ? (
          <Empty 
            description="Không tìm thấy node" 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: '8px 0' }}
          />
        ) : null
      }
    >
      <Input
        prefix={<SearchOutlined />}
        placeholder={placeholder}
        allowClear
      />
    </AutoComplete>
  );
};

