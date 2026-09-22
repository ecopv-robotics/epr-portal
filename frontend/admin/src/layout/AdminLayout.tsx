import { AuditOutlined, DashboardOutlined, FileSearchOutlined, LogoutOutlined, SettingOutlined, ShopOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
import { ProLayout } from '@ant-design/pro-components';
import { Avatar, Dropdown, Space, Tag } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import type { User } from '../types';

const routes=[{path:'/dashboard',name:'Dashboard',icon:<DashboardOutlined/>},{path:'/applications',name:'递单管理',icon:<FileSearchOutlined/>},{path:'/agents',name:'代理管理',icon:<ShopOutlined/>},{path:'/direct-customers',name:'直客管理',icon:<UserOutlined/>},{path:'/employees',name:'员工与任务',icon:<TeamOutlined/>},{path:'/templates',name:'模板配置',icon:<SettingOutlined/>}];
export default function AdminLayout(){const nav=useNavigate(),loc=useLocation();const user=JSON.parse(localStorage.getItem('epr_admin_user')||'{}') as User;return <ProLayout title="EPR FLOW" logo={<AuditOutlined/>} layout="mix" fixedHeader fixSiderbar route={{routes}} location={{pathname:loc.pathname}} menuItemRender={(item,dom)=><span onClick={()=>item.path&&nav(item.path)}>{dom}</span>} avatarProps={{src:<Avatar icon={<UserOutlined/>}/>,title:<Space>{user.username}<Tag color={user.role==='ADMIN'?'blue':'cyan'}>{user.role==='ADMIN'?'管理员':'员工'}</Tag></Space>,render:(_,dom)=><Dropdown menu={{items:[{key:'logout',icon:<LogoutOutlined/>,label:'退出登录',onClick:()=>{localStorage.clear();nav('/login')}}]}}>{dom}</Dropdown>}} contentStyle={{padding:24}}><Outlet/></ProLayout>}
