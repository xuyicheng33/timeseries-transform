/**
 * 模型模板管理页面
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Modal,
  Form,
  message,
  Popconfirm,
  Tooltip,
  Row,
  Col,
  Descriptions,
  Typography,
  Collapse,
  Badge,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CopyOutlined,
  RocketOutlined,
  ReloadOutlined,
  SettingOutlined,
  CodeOutlined,
  StarFilled,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  getModelTemplates,
  getModelCategories,
  getModelTemplate,
  createModelTemplate,
  updateModelTemplate,
  deleteModelTemplate,
  duplicateModelTemplate,
  initPresetTemplates,
} from '@/api/modelTemplates';
import type {
  ModelTemplate,
  ModelTemplateCreate,
  ModelTemplateUpdate,
  ModelCategory,
  TaskType,
  ModelCategoryOption,
} from '@/types/modelTemplate';
import { MODEL_CATEGORY_CONFIG, TASK_TYPE_CONFIG } from '@/types/modelTemplate';
import { useAuth } from '@/contexts/AuthContext';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Paragraph } = Typography;

const ModelTemplateManager: React.FC = () => {
  const { user } = useAuth();
  
  // 列表状态
  const [templates, setTemplates] = useState<ModelTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 筛选状态
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<ModelCategory | undefined>();
  const [categories, setCategories] = useState<ModelCategoryOption[]>([]);

  // 弹窗状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);

  // 当前操作的模板
  const [currentTemplate, setCurrentTemplate] = useState<ModelTemplate | null>(null);

  // 表单
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  // 加载模板列表
  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getModelTemplates({
        page,
        page_size: pageSize,
        search: searchText || undefined,
        category: categoryFilter,
      });
      setTemplates(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('加载模型模板列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchText, categoryFilter]);

  // 加载类别列表
  const loadCategories = async () => {
    try {
      const response = await getModelCategories();
      setCategories(response);
    } catch (error) {
      console.error('加载类别失败', error);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    loadCategories();
  }, []);

  // 初始化预置模板
  const handleInitPresets = async () => {
    try {
      const result = await initPresetTemplates();
      message.success(`${result.message}，新增 ${result.created} 个，跳过 ${result.skipped} 个`);
      loadTemplates();
      loadCategories();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '初始化失败');
    }
  };

  // 创建模板
  const handleCreate = async (values: any) => {
    try {
      const data: ModelTemplateCreate = {
        name: values.name,
        version: values.version || '1.0',
        category: values.category || 'deep_learning',
        description: values.description || '',
        hyperparameters: values.hyperparameters ? JSON.parse(values.hyperparameters) : {},
        training_config: values.training_config ? JSON.parse(values.training_config) : {},
        task_types: values.task_types || [],
        recommended_features: values.recommended_features || '',
        is_public: values.is_public || false,
      };
      await createModelTemplate(data);
      message.success('创建成功');
      setCreateModalVisible(false);
      createForm.resetFields();
      loadTemplates();
      loadCategories();
    } catch (error: any) {
      if (error?.message?.includes('JSON')) {
        message.error('JSON 格式错误，请检查超参数或训练配置');
      } else {
        message.error('创建失败');
      }
    }
  };

  // 查看详情
  const handleViewDetail = async (id: number) => {
    try {
      const detail = await getModelTemplate(id);
      setCurrentTemplate(detail);
      setDetailModalVisible(true);
    } catch (error) {
      message.error('加载详情失败');
    }
  };

  // 编辑模板
  const handleEdit = async (template: ModelTemplate) => {
    setCurrentTemplate(template);
    editForm.setFieldsValue({
      name: template.name,
      version: template.version,
      category: template.category,
      description: template.description,
      hyperparameters: JSON.stringify(template.hyperparameters, null, 2),
      training_config: JSON.stringify(template.training_config, null, 2),
      task_types: template.task_types,
      recommended_features: template.recommended_features,
      is_public: template.is_public,
    });
    setEditModalVisible(true);
  };

  const handleEditSubmit = async (values: any) => {
    if (!currentTemplate) return;
    try {
      const data: ModelTemplateUpdate = {
        name: values.name,
        version: values.version,
        category: values.category,
        description: values.description,
        hyperparameters: values.hyperparameters ? JSON.parse(values.hyperparameters) : undefined,
        training_config: values.training_config ? JSON.parse(values.training_config) : undefined,
        task_types: values.task_types,
        recommended_features: values.recommended_features,
        is_public: values.is_public,
      };
      await updateModelTemplate(currentTemplate.id, data);
      message.success('更新成功');
      setEditModalVisible(false);
      loadTemplates();
    } catch (error: any) {
      if (error?.message?.includes('JSON')) {
        message.error('JSON 格式错误，请检查超参数或训练配置');
      } else {
        message.error('更新失败');
      }
    }
  };

  // 删除模板
  const handleDelete = async (id: number) => {
    try {
      await deleteModelTemplate(id);
      message.success('删除成功');
      loadTemplates();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  // 复制模板
  const handleDuplicate = async (id: number) => {
    try {
      await duplicateModelTemplate(id);
      message.success('复制成功');
      loadTemplates();
    } catch (error) {
      message.error('复制失败');
    }
  };

  // 渲染类别标签
  const renderCategoryTag = (category: string) => {
    const config = MODEL_CATEGORY_CONFIG[category as ModelCategory] || MODEL_CATEGORY_CONFIG.other;
    return (
      <Tag color={config.color}>
        {config.icon} {config.label}
      </Tag>
    );
  };

  // 渲染任务类型标签
  const renderTaskTypes = (types: TaskType[]) => {
    if (!types || types.length === 0) return <Text type="secondary">-</Text>;
    return (
      <Space size={[0, 4]} wrap>
        {types.map((type) => {
          const config = TASK_TYPE_CONFIG[type];
          return config ? (
            <Tag key={type} color={config.color} style={{ margin: 2 }}>
              {config.label}
            </Tag>
          ) : null;
        })}
      </Space>
    );
  };

  // 表格列定义
  const columns: ColumnsType<ModelTemplate> = [
    {
      title: '模型名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (text, record) => (
        <Space>
          <a onClick={() => handleViewDetail(record.id)}>
            <RocketOutlined style={{ marginRight: 4 }} />
            {text}
          </a>
          {record.is_system && (
            <Tooltip title="系统预置模板">
              <StarFilled style={{ color: '#faad14' }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 80,
      render: (text) => <Tag>v{text}</Tag>,
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: renderCategoryTag,
    },
    {
      title: '适用任务',
      dataIndex: 'task_types',
      key: 'task_types',
      width: 200,
      render: renderTaskTypes,
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100,
      align: 'center',
      sorter: (a, b) => a.usage_count - b.usage_count,
      render: (count) => (
        <Badge count={count} showZero color={count > 0 ? 'blue' : 'default'} />
      ),
    },
    {
      title: '公开',
      dataIndex: 'is_public',
      key: 'is_public',
      width: 80,
      align: 'center',
      render: (isPublic, record) =>
        record.is_system ? (
          <Tag color="gold">系统</Tag>
        ) : isPublic ? (
          <Tag color="green">公开</Tag>
        ) : (
          <Tag>私有</Tag>
        ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record.id)}
            />
          </Tooltip>
          <Tooltip title="复制">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleDuplicate(record.id)}
            />
          </Tooltip>
          {(!record.is_system || user?.is_admin) && (
            <>
              <Tooltip title="编辑">
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                />
              </Tooltip>
              <Popconfirm
                title="确定删除此模板？"
                onConfirm={() => handleDelete(record.id)}
                okText="确定"
                cancelText="取消"
              >
                <Tooltip title="删除">
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                </Tooltip>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  // 模板表单
  const renderTemplateForm = (form: any, _isEdit: boolean = false) => (
    <Form form={form} layout="vertical">
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="如: LSTM, Transformer, XGBoost" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="version" label="版本号" initialValue="1.0">
            <Input placeholder="如: 1.0, 2.0" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="category" label="类别" initialValue="deep_learning">
            <Select>
              {Object.entries(MODEL_CATEGORY_CONFIG).map(([key, config]) => (
                <Option key={key} value={key}>
                  {config.icon} {config.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="task_types" label="适用任务">
            <Select mode="multiple" placeholder="选择适用的任务类型">
              {Object.entries(TASK_TYPE_CONFIG).map(([key, config]) => (
                <Option key={key} value={key}>
                  {config.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Form.Item name="description" label="描述">
        <TextArea rows={2} placeholder="模型描述" />
      </Form.Item>

      <Form.Item
        name="hyperparameters"
        label={
          <Space>
            <SettingOutlined />
            超参数 (JSON)
          </Space>
        }
        rules={[
          {
            validator: async (_, value) => {
              if (value) {
                try {
                  JSON.parse(value);
                } catch {
                  throw new Error('请输入有效的 JSON 格式');
                }
              }
            },
          },
        ]}
      >
        <TextArea
          rows={6}
          placeholder={`{
  "hidden_size": 64,
  "num_layers": 2,
  "dropout": 0.2
}`}
          style={{ fontFamily: 'monospace' }}
        />
      </Form.Item>

      <Form.Item
        name="training_config"
        label={
          <Space>
            <CodeOutlined />
            训练配置 (JSON)
          </Space>
        }
        rules={[
          {
            validator: async (_, value) => {
              if (value) {
                try {
                  JSON.parse(value);
                } catch {
                  throw new Error('请输入有效的 JSON 格式');
                }
              }
            },
          },
        ]}
      >
        <TextArea
          rows={6}
          placeholder={`{
  "optimizer": "adam",
  "learning_rate": 0.001,
  "batch_size": 32,
  "epochs": 100
}`}
          style={{ fontFamily: 'monospace' }}
        />
      </Form.Item>

      <Form.Item name="recommended_features" label="推荐使用场景">
        <TextArea rows={2} placeholder="描述该模型适合什么样的数据特征" />
      </Form.Item>

      <Form.Item name="is_public" label="是否公开" valuePropName="checked">
        <Select defaultValue={false}>
          <Option value={false}>私有（仅自己可见）</Option>
          <Option value={true}>公开（所有用户可见）</Option>
        </Select>
      </Form.Item>
    </Form>
  );

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <RocketOutlined />
            模型模板管理
          </Space>
        }
        extra={
          <Space>
            {user?.is_admin && (
              <Popconfirm
                title="初始化预置模板"
                description="将添加系统预置的模型模板（已存在的会跳过）"
                onConfirm={handleInitPresets}
                okText="确定"
                cancelText="取消"
              >
                <Button icon={<ThunderboltOutlined />}>
                  初始化预置模板
                </Button>
              </Popconfirm>
            )}
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                createForm.resetFields();
                setCreateModalVisible(true);
              }}
            >
              新建模板
            </Button>
          </Space>
        }
      >
        {/* 筛选栏 */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Input
            placeholder="搜索名称/描述"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={() => {
              setPage(1);
              loadTemplates();
            }}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            placeholder="类别筛选"
            value={categoryFilter}
            onChange={(v) => {
              setCategoryFilter(v);
              setPage(1);
            }}
            style={{ width: 150 }}
            allowClear
          >
            {categories.map((cat) => (
              <Option key={cat.value} value={cat.value}>
                {MODEL_CATEGORY_CONFIG[cat.value]?.icon} {MODEL_CATEGORY_CONFIG[cat.value]?.label || cat.label} ({cat.count})
              </Option>
            ))}
          </Select>
          <Button icon={<ReloadOutlined />} onClick={loadTemplates}>
            刷新
          </Button>
        </Space>

        {/* 表格 */}
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
        />
      </Card>

      {/* 创建模板弹窗 */}
      <Modal
        title="新建模型模板"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={() => createForm.submit()}
        width={700}
        okText="创建"
        cancelText="取消"
      >
        {renderTemplateForm(createForm)}
        <Form form={createForm} onFinish={handleCreate} style={{ display: 'none' }} />
      </Modal>

      {/* 编辑模板弹窗 */}
      <Modal
        title="编辑模型模板"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={() => editForm.submit()}
        width={700}
        okText="保存"
        cancelText="取消"
      >
        {renderTemplateForm(editForm, true)}
        <Form form={editForm} onFinish={handleEditSubmit} style={{ display: 'none' }} />
      </Modal>

      {/* 模板详情弹窗 */}
      <Modal
        title={
          <Space>
            <RocketOutlined />
            {currentTemplate?.name}
            {currentTemplate?.is_system && (
              <Tag color="gold">
                <StarFilled /> 系统模板
              </Tag>
            )}
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setDetailModalVisible(false)}>关闭</Button>
            <Button
              icon={<CopyOutlined />}
              onClick={() => {
                if (currentTemplate) {
                  handleDuplicate(currentTemplate.id);
                  setDetailModalVisible(false);
                }
              }}
            >
              复制为新模板
            </Button>
          </Space>
        }
        width={800}
      >
        {currentTemplate && (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="版本">
                <Tag>v{currentTemplate.version}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="类别">
                {renderCategoryTag(currentTemplate.category)}
              </Descriptions.Item>
              <Descriptions.Item label="适用任务" span={2}>
                {renderTaskTypes(currentTemplate.task_types)}
              </Descriptions.Item>
              <Descriptions.Item label="使用次数">
                <Badge count={currentTemplate.usage_count} showZero />
              </Descriptions.Item>
              <Descriptions.Item label="公开状态">
                {currentTemplate.is_system ? (
                  <Tag color="gold">系统模板</Tag>
                ) : currentTemplate.is_public ? (
                  <Tag color="green">公开</Tag>
                ) : (
                  <Tag>私有</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(currentTemplate.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {new Date(currentTemplate.updated_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                <Paragraph style={{ marginBottom: 0 }}>
                  {currentTemplate.description || '-'}
                </Paragraph>
              </Descriptions.Item>
              <Descriptions.Item label="推荐场景" span={2}>
                <Paragraph style={{ marginBottom: 0 }}>
                  {currentTemplate.recommended_features || '-'}
                </Paragraph>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Collapse
              defaultActiveKey={['hyperparameters', 'training_config']}
              items={[
                {
                  key: 'hyperparameters',
                  label: (
                    <Space>
                      <SettingOutlined />
                      超参数配置
                    </Space>
                  ),
                  children: (
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        overflow: 'auto',
                        maxHeight: 300,
                        margin: 0,
                      }}
                    >
                      {JSON.stringify(currentTemplate.hyperparameters, null, 2) || '{}'}
                    </pre>
                  ),
                },
                {
                  key: 'training_config',
                  label: (
                    <Space>
                      <CodeOutlined />
                      训练配置
                    </Space>
                  ),
                  children: (
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        overflow: 'auto',
                        maxHeight: 300,
                        margin: 0,
                      }}
                    >
                      {JSON.stringify(currentTemplate.training_config, null, 2) || '{}'}
                    </pre>
                  ),
                },
              ]}
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ModelTemplateManager;

