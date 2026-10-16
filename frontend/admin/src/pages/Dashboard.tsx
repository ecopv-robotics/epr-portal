import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileDoneOutlined,
  FormOutlined,
  LoginOutlined,
  SendOutlined,
  SyncOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { PageContainer, StatisticCard } from '@ant-design/pro-components';
import { Button, Card, Col, Row, Spin, Table, Tag, message } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import type { Dashboard as DashboardData, DeliveryDashboardTask, DeliveryStage } from '../types';

const deliveryStageMeta: Record<DeliveryStage, { text: string; color: string }> = {
  RECEIVED: { text: '待递交服务商', color: 'blue' },
  PROVIDER_SUBMITTED: { text: '服务商处理中', color: 'cyan' },
  SUPPLEMENT_FOLLOW_UP: { text: '补件跟进', color: 'orange' },
  COUNTERSIGN_PENDING: { text: '待客户二次回签', color: 'gold' },
  COUNTERSIGNED: { text: '待官方下证', color: 'purple' },
  COMPLETED: { text: '已完成', color: 'green' },
};

function DeliveryDashboard({ data }: { data: DashboardData }) {
  const nav = useNavigate();
  const counts = data.delivery_stage_counts;
  const active = data.delivery_tasks.filter(task => task.stage !== 'COMPLETED').length;
  const cards = [
    { title: '待递交服务商', value: counts.RECEIVED || 0, color: '#1677ff', icon: <SendOutlined /> },
    { title: '服务商处理中', value: counts.PROVIDER_SUBMITTED || 0, color: '#13a8a8', icon: <TeamOutlined /> },
    { title: '补件跟进', value: counts.SUPPLEMENT_FOLLOW_UP || 0, color: '#fa8c16', icon: <SyncOutlined /> },
    { title: '待客户回签', value: counts.COUNTERSIGN_PENDING || 0, color: '#d4b106', icon: <ClockCircleOutlined /> },
    { title: '待官方下证', value: counts.COUNTERSIGNED || 0, color: '#722ed1', icon: <ClockCircleOutlined /> },
    { title: '已完成', value: counts.COMPLETED || 0, color: '#52c41a', icon: <CheckCircleOutlined /> },
  ];

  return <PageContainer title="交付工作台" subTitle="查看本人负责项目的交付进度，并快速进入任务办理">
    <Row gutter={[16, 16]}>
      {cards.map(card => <Col xs={24} sm={12} lg={8} flex="1 1 210px" key={card.title}>
        <StatisticCard statistic={{ title: card.title, value: card.value, valueStyle: { color: card.color }, icon: card.icon }} />
      </Col>)}
    </Row>
    <Card title="我的交付任务" className="dashboard-second" extra={<Tag color="blue">在办 {active}</Tag>}>
      <Table<DeliveryDashboardTask>
        rowKey="application_id"
        dataSource={data.delivery_tasks}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        locale={{ emptyText: '当前没有分配给你的交付任务' }}
        onRow={record => ({ onDoubleClick: () => nav(`/applications/${record.application_id}`) })}
        columns={[
          { title: '申请编号', dataIndex: 'application_no' },
          { title: '客户公司', dataIndex: 'company_name', render: value => value || '未填写' },
          { title: '国家/服务', render: (_, record) => <><div>{record.country}</div><span className="muted">{record.service_type}</span></> },
          { title: '交付状态', dataIndex: 'stage', render: stage => <Tag color={deliveryStageMeta[stage as DeliveryStage].color}>{deliveryStageMeta[stage as DeliveryStage].text}</Tag> },
          { title: '最近更新', dataIndex: 'updated_time', render: value => dayjs(value).format('YYYY-MM-DD HH:mm') },
          { title: '操作', render: (_, record) => <Button type="link" icon={<LoginOutlined />} onClick={() => nav(`/applications/${record.application_id}`)}>进入任务</Button> },
        ]}
      />
    </Card>
  </PageContainer>;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData>();
  useEffect(() => {
    api.get<DashboardData>('/admin/dashboard')
      .then(response => setData(response.data))
      .catch(() => message.error('工作台加载失败'));
  }, []);
  if (!data) return <Spin />;
  if (data.role_code === 'DELIVERY') return <DeliveryDashboard data={data} />;

  return <PageContainer title="Dashboard" subTitle="递单审核与任务概览">
    <Row gutter={[16, 16]}>
      <Col xs={24} md={12} xl={6}><StatisticCard statistic={{ title: '全部递单', value: data.total, icon: <FileDoneOutlined /> }} /></Col>
      <Col xs={24} md={12} xl={6}><StatisticCard statistic={{ title: '待审核', value: data.submitted, valueStyle: { color: '#1677ff' }, icon: <ClockCircleOutlined /> }} /></Col>
      <Col xs={24} md={12} xl={6}><StatisticCard statistic={{ title: '审核中', value: data.reviewing, valueStyle: { color: '#722ed1' }, icon: <FormOutlined /> }} /></Col>
      <Col xs={24} md={12} xl={6}><StatisticCard statistic={{ title: '我的任务', value: data.my_tasks, valueStyle: { color: '#13a8a8' }, icon: <TeamOutlined /> }} /></Col>
    </Row>
    <Row gutter={[16, 16]} className="dashboard-second">
      <Col xs={24} md={12}><Card title="流程状态"><p>待补资料：<strong>{data.need_fix}</strong></p><p>已完成：<strong><CheckCircleOutlined /> {data.completed}</strong></p></Card></Col>
      <Col xs={24} md={12}><Card title="审核规范"><p>所有产品字段与材料规则均从当前服务模板读取。</p><p>补件时须填写明确的审核意见，所有操作写入审计记录。</p></Card></Col>
    </Row>
  </PageContainer>;
}
