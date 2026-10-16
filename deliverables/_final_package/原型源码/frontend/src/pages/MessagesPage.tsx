import { BellOutlined, CheckCircleOutlined, FileTextOutlined } from '@ant-design/icons'
import { Card, List, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import api from '../api'
import type { PortalMessage } from '../types'

const iconFor = (type: string) => type.includes('资料') ? <FileTextOutlined /> : type.includes('进度') || type.includes('完成') ? <CheckCircleOutlined /> : <BellOutlined />

export default function MessagesPage() {
  const [messages, setMessages] = useState<PortalMessage[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => { api.get<PortalMessage[]>('/portal/messages').then(({ data }) => setMessages(data)).finally(() => setLoading(false)) }, [])
  return <div className="page-container"><div className="page-heading"><div><Typography.Title level={2}>消息中心</Typography.Title><Typography.Text type="secondary">查看服务通知、资料提醒和续费消息</Typography.Text></div></div><Card className="data-card"><List loading={loading} itemLayout="horizontal" dataSource={messages} renderItem={item => <List.Item actions={[<Typography.Text type="secondary" key="time">{dayjs(item.created_time).format('MM-DD HH:mm')}</Typography.Text>]}><List.Item.Meta avatar={<span className="message-icon">{iconFor(item.message_type)}</span>} title={<span>{item.title} <Tag color="blue">{item.message_type}</Tag></span>} description={item.description} /></List.Item>} /></Card></div>
}
