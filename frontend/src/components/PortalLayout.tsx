import { AppstoreOutlined, BellOutlined, FileTextOutlined, HomeOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { Avatar, Dropdown, Layout, Menu, Space } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { clearSession, getUser } from '../auth'
import Logo from './Logo'

const { Header, Sider, Content } = Layout

export default function PortalLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = getUser()
  const selected = location.pathname.startsWith('/application') ? '/applications' : location.pathname

  return (
    <Layout className="app-shell">
      <Sider width={224} theme="light" className="portal-sider">
        <div className="sider-logo"><Logo /></div>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          onClick={({ key }) => key !== 'disabled' && navigate(key)}
          items={[
            { key: '/home', icon: <HomeOutlined />, label: '首页', disabled: true },
            { key: '/applications', icon: <FileTextOutlined />, label: '我的递单' },
            { key: '/companies', icon: <AppstoreOutlined />, label: '企业资料' },
            { key: 'profile', icon: <UserOutlined />, label: '个人中心', disabled: true },
          ]}
        />
      </Sider>
      <Layout>
        <Header className="portal-header">
          <span className="header-slogan">让合规更简单 · Make Compliance Easier</span>
          <Space size={20}>
            <BellOutlined className="header-icon" />
            <Dropdown menu={{ items: [{ key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: () => { clearSession(); navigate('/login') } }] }}>
              <Space className="user-menu"><Avatar size="small" icon={<UserOutlined />} />{user?.username ?? '用户'}</Space>
            </Dropdown>
          </Space>
        </Header>
        <Content className="portal-content"><Outlet /></Content>
      </Layout>
    </Layout>
  )
}
