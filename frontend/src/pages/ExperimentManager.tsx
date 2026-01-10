/**
 * 实验管理页面
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
  Badge,
  Empty,
  Row,
  Col,
  Statistic,
  Descriptions,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ExperimentOutlined,
  TagsOutlined,
  ReloadOutlined,
  TrophyOutlined,
  BarChartOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  getExperiments,
  createExperiment,
  getExperiment,
  updateExperiment,
  deleteExperiment,
  addResultsToExperiment,
  removeResultsFromExperiment,
  getExperimentSummary,
  getAllTags,
} from '@/api/experiments';
import { getResults } from '@/api/results';
import { getDatasets } from '@/api/datasets';
import type {
  Experiment,
  ExperimentDetail,
  ExperimentStatus,
  ExperimentSummary,
  ExperimentCreateRequest,
  ExperimentUpdateRequest,
} from '@/types/experiment';
import type { Result, Dataset } from '@/types';

const { TextArea } = Input;
const { Option } = Select;

// 状态配置
const STATUS_CONFIG: Record<ExperimentStatus, { color: string; text: string }> = {
  draft: { color: 'default', text: '草稿' },
  running: { color: 'processing', text: '进行中' },
  completed: { color: 'success', text: '已完成' },
  archived: { color: 'warning', text: '已归档' },
};

const ExperimentManager: React.FC = () => {
  // 列表状态
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 筛选状态
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<ExperimentStatus | undefined>();
  const [tagFilter, setTagFilter] = useState<string | undefined>();
  const [allTags, setAllTags] = useState<string[]>([]);

  // 弹窗状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [addResultsModalVisible, setAddResultsModalVisible] = useState(false);

  // 当前操作的实验组
  const [currentExperiment, setCurrentExperiment] = useState<ExperimentDetail | null>(null);
  const [currentSummary, setCurrentSummary] = useState<ExperimentSummary | null>(null);

  // 表单
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  // 可选数据
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [availableResults, setAvailableResults] = useState<Result[]>([]);
  const [selectedResultIds, setSelectedResultIds] = useState<number[]>([]);

  // 加载实验组列表
  const loadExperiments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getExperiments({
        page,
        page_size: pageSize,
        search: searchText || undefined,
        status: statusFilter,
        tag: tagFilter,
      });
      setExperiments(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('加载实验组列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchText, statusFilter, tagFilter]);

  // 加载标签列表
  const loadTags = async () => {
    try {
      const response = await getAllTags();
      setAllTags(response.tags);
    } catch (error) {
      console.error('加载标签失败', error);
    }
  };

  // 加载数据集列表
  const loadDatasets = async () => {
    try {
      const response = await getDatasets(1, 100);
      setDatasets(response.items);
    } catch (error) {
      console.error('加载数据集失败', error);
    }
  };

  // 加载可用结果列表
  const loadAvailableResults = async () => {
    try {
      const response = await getResults(undefined, undefined, 1, 200);
      setAvailableResults(response.items);
    } catch (error) {
      console.error('加载结果列表失败', error);
    }
  };

  useEffect(() => {
    loadExperiments();
  }, [loadExperiments]);

  useEffect(() => {
    loadTags();
    loadDatasets();
  }, []);

  // 创建实验组
  const handleCreate = async (values: ExperimentCreateRequest) => {
    try {
      await createExperiment(values);
      message.success('创建成功');
      setCreateModalVisible(false);
      createForm.resetFields();
      loadExperiments();
      loadTags();
    } catch (error) {
      message.error('创建失败');
    }
  };

  // 查看详情
  const handleViewDetail = async (id: number) => {
    try {
      const [detail, summary] = await Promise.all([
        getExperiment(id),
        getExperimentSummary(id),
      ]);
      setCurrentExperiment(detail);
      setCurrentSummary(summary);
      setDetailModalVisible(true);
    } catch (error) {
      message.error('加载详情失败');
    }
  };

  // 编辑实验组
  const handleEdit = async (experiment: Experiment) => {
    setCurrentExperiment(experiment as ExperimentDetail);
    editForm.setFieldsValue({
      name: experiment.name,
      description: experiment.description,
      objective: experiment.objective,
      status: experiment.status,
      tags: experiment.tags,
      conclusion: experiment.conclusion,
      dataset_id: experiment.dataset_id,
    });
    setEditModalVisible(true);
  };

  const handleEditSubmit = async (values: ExperimentUpdateRequest) => {
    if (!currentExperiment) return;
    try {
      await updateExperiment(currentExperiment.id, values);
      message.success('更新成功');
      setEditModalVisible(false);
      loadExperiments();
      loadTags();
    } catch (error) {
      message.error('更新失败');
    }
  };

  // 删除实验组
  const handleDelete = async (id: number) => {
    try {
      await deleteExperiment(id);
      message.success('删除成功');
      loadExperiments();
    } catch (error) {
      message.error('删除失败');
    }
  };

  // 添加结果
  const handleOpenAddResults = async (experiment: Experiment) => {
    setCurrentExperiment(experiment as ExperimentDetail);
    await loadAvailableResults();
    setSelectedResultIds([]);
    setAddResultsModalVisible(true);
  };

  const handleAddResults = async () => {
    if (!currentExperiment || selectedResultIds.length === 0) return;
    try {
      await addResultsToExperiment(currentExperiment.id, {
        result_ids: selectedResultIds,
      });
      message.success('添加成功');
      setAddResultsModalVisible(false);
      loadExperiments();
    } catch (error) {
      message.error('添加失败');
    }
  };

  // 移除结果
  const handleRemoveResult = async (resultId: number) => {
    if (!currentExperiment) return;
    try {
      await removeResultsFromExperiment(currentExperiment.id, {
        result_ids: [resultId],
      });
      message.success('移除成功');
      // 刷新详情
      const detail = await getExperiment(currentExperiment.id);
      setCurrentExperiment(detail);
    } catch (error) {
      message.error('移除失败');
    }
  };

  // 表格列定义
  const columns: ColumnsType<Experiment> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text, record) => (
        <a onClick={() => handleViewDetail(record.id)}>
          <ExperimentOutlined style={{ marginRight: 8 }} />
          {text}
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ExperimentStatus) => (
        <Badge
          status={STATUS_CONFIG[status].color as any}
          text={STATUS_CONFIG[status].text}
        />
      ),
    },
    {
      title: '关联数据集',
      dataIndex: 'dataset_name',
      key: 'dataset_name',
      width: 150,
      render: (text) => text || <span style={{ color: '#999' }}>-</span>,
    },
    {
      title: '结果数量',
      dataIndex: 'result_count',
      key: 'result_count',
      width: 100,
      align: 'center',
      render: (count) => (
        <Tag color={count > 0 ? 'blue' : 'default'}>{count}</Tag>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags: string[]) =>
        tags?.length > 0 ? (
          <Space size={[0, 4]} wrap>
            {tags.slice(0, 3).map((tag) => (
              <Tag key={tag} color="cyan">
                {tag}
              </Tag>
            ))}
            {tags.length > 3 && <Tag>+{tags.length - 3}</Tag>}
          </Space>
        ) : (
          <span style={{ color: '#999' }}>-</span>
        ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
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
          <Tooltip title="添加结果">
            <Button
              type="text"
              size="small"
              icon={<PlusOutlined />}
              onClick={() => handleOpenAddResults(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此实验组？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 渲染最佳指标
  const renderBestMetric = (
    label: string,
    info: { result_id: number; value: number; model_name: string } | null,
    _isHigherBetter: boolean = false
  ) => {
    if (!info) return null;
    return (
      <Statistic
        title={
          <Space>
            <TrophyOutlined style={{ color: '#faad14' }} />
            {label}
          </Space>
        }
        value={info.value}
        precision={6}
        suffix={
          <Tooltip title={`模型: ${info.model_name}`}>
            <Tag color="gold" style={{ marginLeft: 8 }}>
              {info.model_name}
            </Tag>
          </Tooltip>
        }
      />
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <ExperimentOutlined />
            实验管理
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              createForm.resetFields();
              setCreateModalVisible(true);
            }}
          >
            新建实验组
          </Button>
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
              loadExperiments();
            }}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            placeholder="状态筛选"
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            style={{ width: 120 }}
            allowClear
          >
            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
              <Option key={key} value={key}>
                {config.text}
              </Option>
            ))}
          </Select>
          <Select
            placeholder="标签筛选"
            value={tagFilter}
            onChange={(v) => {
              setTagFilter(v);
              setPage(1);
            }}
            style={{ width: 150 }}
            allowClear
          >
            {allTags.map((tag) => (
              <Option key={tag} value={tag}>
                <TagsOutlined /> {tag}
              </Option>
            ))}
          </Select>
          <Button icon={<ReloadOutlined />} onClick={loadExperiments}>
            刷新
          </Button>
        </Space>

        {/* 表格 */}
        <Table
          columns={columns}
          dataSource={experiments}
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

      {/* 创建实验组弹窗 */}
      <Modal
        title="新建实验组"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="name"
            label="实验名称"
            rules={[{ required: true, message: '请输入实验名称' }]}
          >
            <Input placeholder="输入实验名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="实验描述" />
          </Form.Item>
          <Form.Item name="objective" label="实验目标/假设">
            <TextArea rows={2} placeholder="描述实验目标或假设" />
          </Form.Item>
          <Form.Item name="dataset_id" label="关联数据集">
            <Select placeholder="选择数据集（可选）" allowClear>
              {datasets.map((ds) => (
                <Option key={ds.id} value={ds.id}>
                  {ds.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入标签后回车" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑实验组弹窗 */}
      <Modal
        title="编辑实验组"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEditSubmit}>
          <Form.Item
            name="name"
            label="实验名称"
            rules={[{ required: true, message: '请输入实验名称' }]}
          >
            <Input placeholder="输入实验名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="实验描述" />
          </Form.Item>
          <Form.Item name="objective" label="实验目标/假设">
            <TextArea rows={2} placeholder="描述实验目标或假设" />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select>
              {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                <Option key={key} value={key}>
                  {config.text}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="dataset_id" label="关联数据集">
            <Select placeholder="选择数据集（可选）" allowClear>
              {datasets.map((ds) => (
                <Option key={ds.id} value={ds.id}>
                  {ds.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入标签后回车" />
          </Form.Item>
          <Form.Item name="conclusion" label="实验结论">
            <TextArea rows={4} placeholder="记录实验结论" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 实验详情弹窗 */}
      <Modal
        title={
          <Space>
            <ExperimentOutlined />
            {currentExperiment?.name}
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={900}
      >
        {currentExperiment && (
          <Tabs
            items={[
              {
                key: 'info',
                label: (
                  <span>
                    <FileTextOutlined />
                    基本信息
                  </span>
                ),
                children: (
                  <Descriptions column={2} bordered size="small">
                    <Descriptions.Item label="状态">
                      <Badge
                        status={STATUS_CONFIG[currentExperiment.status].color as any}
                        text={STATUS_CONFIG[currentExperiment.status].text}
                      />
                    </Descriptions.Item>
                    <Descriptions.Item label="关联数据集">
                      {currentExperiment.dataset_name || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="结果数量">
                      {currentExperiment.result_count}
                    </Descriptions.Item>
                    <Descriptions.Item label="创建时间">
                      {new Date(currentExperiment.created_at).toLocaleString()}
                    </Descriptions.Item>
                    <Descriptions.Item label="实验目标" span={2}>
                      {currentExperiment.objective || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="描述" span={2}>
                      {currentExperiment.description || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="标签" span={2}>
                      {currentExperiment.tags?.length > 0 ? (
                        <Space wrap>
                          {currentExperiment.tags.map((tag) => (
                            <Tag key={tag} color="cyan">
                              {tag}
                            </Tag>
                          ))}
                        </Space>
                      ) : (
                        '-'
                      )}
                    </Descriptions.Item>
                    <Descriptions.Item label="实验结论" span={2}>
                      {currentExperiment.conclusion || '-'}
                    </Descriptions.Item>
                  </Descriptions>
                ),
              },
              {
                key: 'summary',
                label: (
                  <span>
                    <BarChartOutlined />
                    统计汇总
                  </span>
                ),
                children: currentSummary ? (
                  <div>
                    <Row gutter={[16, 16]}>
                      <Col span={8}>
                        <Card size="small">
                          <Statistic
                            title="结果数量"
                            value={currentSummary.result_count}
                            prefix={<ExperimentOutlined />}
                          />
                        </Card>
                      </Col>
                      <Col span={16}>
                        <Card size="small" title="涉及模型">
                          <Space wrap>
                            {currentSummary.model_names.map((name) => (
                              <Tag key={name} color="blue">
                                {name}
                              </Tag>
                            ))}
                          </Space>
                        </Card>
                      </Col>
                    </Row>

                    {currentSummary.result_count > 0 && (
                      <>
                        <Card
                          size="small"
                          title="最佳指标"
                          style={{ marginTop: 16 }}
                        >
                          <Row gutter={16}>
                            <Col span={8}>
                              {renderBestMetric('最佳 MSE', currentSummary.best_mse)}
                            </Col>
                            <Col span={8}>
                              {renderBestMetric('最佳 RMSE', currentSummary.best_rmse)}
                            </Col>
                            <Col span={8}>
                              {renderBestMetric('最佳 MAE', currentSummary.best_mae)}
                            </Col>
                          </Row>
                          <Row gutter={16} style={{ marginTop: 16 }}>
                            <Col span={8}>
                              {renderBestMetric('最佳 R²', currentSummary.best_r2, true)}
                            </Col>
                            <Col span={8}>
                              {renderBestMetric('最佳 MAPE', currentSummary.best_mape)}
                            </Col>
                          </Row>
                        </Card>

                        {currentSummary.avg_metrics && (
                          <Card
                            size="small"
                            title="平均指标"
                            style={{ marginTop: 16 }}
                          >
                            <Row gutter={16}>
                              <Col span={4}>
                                <Statistic
                                  title="MSE"
                                  value={currentSummary.avg_metrics.mse}
                                  precision={6}
                                />
                              </Col>
                              <Col span={4}>
                                <Statistic
                                  title="RMSE"
                                  value={currentSummary.avg_metrics.rmse}
                                  precision={6}
                                />
                              </Col>
                              <Col span={4}>
                                <Statistic
                                  title="MAE"
                                  value={currentSummary.avg_metrics.mae}
                                  precision={6}
                                />
                              </Col>
                              <Col span={4}>
                                <Statistic
                                  title="R²"
                                  value={currentSummary.avg_metrics.r2}
                                  precision={4}
                                />
                              </Col>
                              <Col span={4}>
                                <Statistic
                                  title="MAPE"
                                  value={currentSummary.avg_metrics.mape}
                                  precision={2}
                                  suffix="%"
                                />
                              </Col>
                            </Row>
                          </Card>
                        )}
                      </>
                    )}
                  </div>
                ) : (
                  <Empty description="暂无统计数据" />
                ),
              },
              {
                key: 'results',
                label: (
                  <span>
                    <BarChartOutlined />
                    关联结果 ({currentExperiment.results?.length || 0})
                  </span>
                ),
                children: (
                  <div>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => handleOpenAddResults(currentExperiment)}
                      style={{ marginBottom: 16 }}
                    >
                      添加结果
                    </Button>
                    {currentExperiment.results?.length > 0 ? (
                      <Table
                        size="small"
                        dataSource={currentExperiment.results}
                        rowKey="id"
                        columns={[
                          { title: '名称', dataIndex: 'name', key: 'name' },
                          {
                            title: '模型',
                            dataIndex: 'model_name',
                            key: 'model_name',
                            render: (text, record) => (
                              <span>
                                {text}
                                {record.model_version && (
                                  <Tag style={{ marginLeft: 4 }}>
                                    v{record.model_version}
                                  </Tag>
                                )}
                              </span>
                            ),
                          },
                          {
                            title: 'MSE',
                            key: 'mse',
                            render: (_, record) =>
                              record.metrics?.mse?.toFixed(6) || '-',
                          },
                          {
                            title: 'R²',
                            key: 'r2',
                            render: (_, record) =>
                              record.metrics?.r2?.toFixed(4) || '-',
                          },
                          {
                            title: '操作',
                            key: 'action',
                            render: (_, record) => (
                              <Popconfirm
                                title="确定从实验组中移除此结果？"
                                onConfirm={() => handleRemoveResult(record.id)}
                              >
                                <Button type="text" size="small" danger>
                                  移除
                                </Button>
                              </Popconfirm>
                            ),
                          },
                        ]}
                        pagination={false}
                      />
                    ) : (
                      <Empty description="暂无关联结果" />
                    )}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Modal>

      {/* 添加结果弹窗 */}
      <Modal
        title="添加结果到实验组"
        open={addResultsModalVisible}
        onCancel={() => setAddResultsModalVisible(false)}
        onOk={handleAddResults}
        okText="添加"
        cancelText="取消"
        width={700}
      >
        <Table
          size="small"
          dataSource={availableResults}
          rowKey="id"
          rowSelection={{
            selectedRowKeys: selectedResultIds,
            onChange: (keys) => setSelectedResultIds(keys as number[]),
          }}
          columns={[
            { title: '名称', dataIndex: 'name', key: 'name' },
            { title: '模型', dataIndex: 'model_name', key: 'model_name' },
            {
              title: 'MSE',
              key: 'mse',
              render: (_, record) => record.metrics?.mse?.toFixed(6) || '-',
            },
            {
              title: 'R²',
              key: 'r2',
              render: (_, record) => record.metrics?.r2?.toFixed(4) || '-',
            },
          ]}
          pagination={{ pageSize: 10 }}
        />
      </Modal>
    </div>
  );
};

export default ExperimentManager;

