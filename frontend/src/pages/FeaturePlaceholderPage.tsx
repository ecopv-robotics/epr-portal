import type { ReactNode } from 'react'
import { AppstoreOutlined } from '@ant-design/icons'
import { Card, Empty, Typography } from 'antd'

export default function FeaturePlaceholderPage({ title, description, icon }: { title: string; description: string; icon?: ReactNode }) {
  return <div className="page-container"><div className="page-heading"><div><Typography.Title level={2}>{title}</Typography.Title><Typography.Text type="secondary">{description}</Typography.Text></div></div><Card className="data-card feature-placeholder"><Empty image={icon || <AppstoreOutlined />} description="该功能入口已完成，业务内容将在后续阶段接入" /></Card></div>
}
