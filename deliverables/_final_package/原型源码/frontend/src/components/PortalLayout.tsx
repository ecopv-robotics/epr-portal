import {
  AppstoreOutlined, BellOutlined, CustomerServiceOutlined, FileProtectOutlined, HomeOutlined,
  LogoutOutlined, MenuOutlined, PlusCircleOutlined, ReloadOutlined, ShoppingCartOutlined, UserOutlined,
} from '@ant-design/icons'
import { Avatar, Badge, Button, Divider, Drawer, Dropdown, Layout, Menu, Popover, Space, Tag, Typography } from 'antd'
import type { MenuProps } from 'antd'
import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import api from '../api'
import { clearSession, getUser } from '../auth'
import type { CartItem, Manager } from '../types'
import Logo from './Logo'

const { Header, Sider, Content } = Layout

const menuItems: MenuProps['items'] = [
  { key: '/services', icon: <PlusCircleOutlined />, label: '购买服务' },
  { key: '/renewals', icon: <ReloadOutlined />, label: '续费服务' },
  { type: 'divider' },
  { key: '/home', icon: <HomeOutlined />, label: '工作台' },
  {
    key: 'epr-services', icon: <FileProtectOutlined />, label: 'EPR服务',
    children: [
      { key: '/epr/registrations', label: 'EPR注册号' },
      { key: '/epr/declarations', label: 'EPR申报' },
    ],
  },
  { type: 'divider' },
  {
    key: 'account-center', icon: <UserOutlined />, label: '账户中心',
    children: [
      { key: '/account/orders', label: '我的订单' },
      { key: '/account/coupons', label: '我的优惠券' },
      { key: '/account/invoices', label: '我的发票' },
      { key: '/account/messages', label: <Space size={8}>我的消息<Badge count={3} size="small" /></Space> },
      { key: '/account/settings', label: '账号设置' },
    ],
  },
  { key: '/apps', icon: <AppstoreOutlined />, label: <Space size={8}>应用中心<Tag color="orange" bordered={false}>NEW</Tag></Space> },
]

function ManagerCard({ manager }: { manager: Manager }) {
  return <div className="manager-card">
    <Typography.Title level={5}>专属客户经理</Typography.Title>
    <Typography.Text type="secondary">{manager.work_hours} 为你提供一对一服务</Typography.Text>
    <Divider />
    <div className="manager-profile">
      <Avatar size={52} className="manager-avatar">{manager.name.slice(0, 1)}</Avatar>
      <div><strong>{manager.name}</strong><Typography.Text type="secondary">{manager.role}</Typography.Text></div>
    </div>
    <div className="manager-contact"><span>联系电话</span><strong>{manager.phone}</strong><Button type="link" size="small" href={`tel:${manager.phone}`}>拨打</Button></div>
    <div className="manager-contact"><span>企业微信</span><strong>{manager.wechat}</strong><Button type="link" size="small">二维码</Button></div>
    <div className="manager-online"><i className={manager.online ? '' : 'offline'} />{manager.online ? '当前在线，通常 5 分钟内回复' : '当前离线，请留言'}</div>
  </div>
}

export default function PortalLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = getUser()
  const [cartCount, setCartCount] = useState(0)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [manager, setManager] = useState<Manager>({ name: 'Norah', role: '专属客户经理', phone: '18120741686', wechat: '18120741686', work_hours: '工作日 09:00–18:00', online: true })
  useEffect(() => {
    const update = () => api.get<CartItem[]>('/portal/cart').then(({ data }) => setCartCount(data.length)).catch(() => undefined)
    void update()
    api.get<Manager>('/portal/manager').then(({ data }) => setManager(data)).catch(() => undefined)
    window.addEventListener('epr-cart-updated', update)
    return () => window.removeEventListener('epr-cart-updated', update)
  }, [])
  const selected = location.pathname.startsWith('/orders')
    ? '/services'
    : location.pathname.startsWith('/application') || location.pathname === '/applications'
      ? '/account/orders'
      : location.pathname === '/messages'
        ? '/account/messages'
        : location.pathname === '/account' || location.pathname === '/companies'
          ? '/account/settings'
          : location.pathname
  const openMenuKeys = [
    ...(location.pathname.startsWith('/epr') ? ['epr-services'] : []),
    ...(selected.startsWith('/account/') ? ['account-center'] : []),
  ]

  return <Layout className="app-shell">
    <Sider width={224} theme="light" className="portal-sider">
      <div className="sider-logo"><Logo /></div>
      <Menu key={location.pathname} mode="inline" selectedKeys={[selected]} defaultOpenKeys={openMenuKeys} onClick={({ key }) => navigate(key)} items={menuItems} />
      <div className="sider-user-card"><Avatar icon={<UserOutlined />} /><div><strong>{user?.username ?? '用户'}</strong><span>企业管理员</span></div></div>
    </Sider>
    <Layout>
      <Header className="portal-header">
        <Button type="text" icon={<MenuOutlined />} className="mobile-menu-button" onClick={() => setMobileMenuOpen(true)} aria-label="打开导航" />
        <span className="header-slogan">让合规更简单 · Make Compliance Easier</span>
        <Space size={10} className="header-actions">
          <Button type="text" icon={<BellOutlined />} className="header-action" />
          <Badge count={cartCount} size="small" offset={[-4, 4]}><Button type="text" icon={<ShoppingCartOutlined />} className="header-action" onClick={() => navigate('/cart')}>购物车</Button></Badge>
          <Popover placement="bottomRight" trigger="click" content={<ManagerCard manager={manager} />} overlayClassName="manager-popover"><Button type="text" icon={<CustomerServiceOutlined />} className="header-action">帮助中心</Button></Popover>
          <Dropdown menu={{ items: [{ key: 'account', icon: <UserOutlined />, label: '账户中心', onClick: () => navigate('/account/settings') }, { type: 'divider' }, { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: () => { clearSession(); navigate('/login') } }] }}>
            <Space className="user-menu"><Avatar size="small" icon={<UserOutlined />} />{user?.username ?? '用户'}</Space>
          </Dropdown>
        </Space>
      </Header>
      <Content className="portal-content"><Outlet /></Content>
      <Drawer title={<Logo />} placement="left" width={280} open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} styles={{ body: { padding: '8px 10px' } }}>
        <Menu key={location.pathname} mode="inline" selectedKeys={[selected]} defaultOpenKeys={openMenuKeys} onClick={({ key }) => { navigate(key); setMobileMenuOpen(false) }} items={menuItems} />
      </Drawer>
    </Layout>
  </Layout>
}
