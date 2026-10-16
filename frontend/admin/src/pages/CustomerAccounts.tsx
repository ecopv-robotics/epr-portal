import { ApartmentOutlined, EyeOutlined, FileTextOutlined, PlusOutlined } from '@ant-design/icons'
import { PageContainer } from '@ant-design/pro-components'
import { Button, Card, Col, Descriptions, Form, Input, Modal, Progress, Row, Space, Statistic, Switch, Table, Tabs, Tag, message } from 'antd'
import axios from 'axios'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { Application, ApplicationStatus, CustomerAccount, CustomerAccountDetail, CustomerCompany, User } from '../types'

type AccountForm = { username:string; email:string; password:string; name:string; contact_name?:string; contact_phone?:string; active?:boolean }
const statusMeta:Record<ApplicationStatus,{text:string;color:string}>={DRAFT:{text:'草稿',color:'default'},SUBMITTED:{text:'待审核',color:'blue'},REVIEWING:{text:'审核中',color:'processing'},NEED_FIX:{text:'待补件',color:'warning'},REGISTERING:{text:'注册中',color:'cyan'},COMPLETED:{text:'已完成',color:'success'}}
const regions:Record<string,string>={MAINLAND_CHINA:'中国大陆',HONG_KONG:'中国香港',EU:'欧盟',OTHER:'其他'}

export default function CustomerAccounts({type}:{type:'AGENT'|'DIRECT'}){
  const navigate=useNavigate(),isAgent=type==='AGENT',endpoint=isAgent?'/admin/agents':'/admin/direct-customers'
  const user=JSON.parse(localStorage.getItem('epr_admin_user')||'{}') as User,isAdmin=user.role==='ADMIN'
  const [items,setItems]=useState<CustomerAccount[]>([]),[open,setOpen]=useState(false),[editing,setEditing]=useState<CustomerAccount>(),[loading,setLoading]=useState(false)
  const [detail,setDetail]=useState<CustomerAccountDetail>(),[detailLoading,setDetailLoading]=useState(false)
  const [form]=Form.useForm<AccountForm>()
  async function load(){setLoading(true);try{setItems((await api.get<CustomerAccount[]>(endpoint)).data)}catch{message.error('客户列表加载失败')}finally{setLoading(false)}}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(()=>{void load()},[endpoint])
  function create(){setEditing(undefined);form.resetFields();setOpen(true)}
  function edit(item:CustomerAccount){setEditing(item);form.setFieldsValue({...item});setOpen(true)}
  async function showDetail(item:CustomerAccount){setDetailLoading(true);try{setDetail((await api.get<CustomerAccountDetail>(`${endpoint}/${item.id}/detail`)).data)}catch{message.error('客户详情加载失败')}finally{setDetailLoading(false)}}
  async function save(){const values=await form.validateFields();try{if(editing){await api.put(`${endpoint}/${editing.id}`,{name:values.name,email:values.email,contact_name:values.contact_name,contact_phone:values.contact_phone,active:values.active})}else{await api.post(endpoint,values)}message.success(editing?'资料已更新':'账号已创建');setOpen(false);await load()}catch(e){message.error(axios.isAxiosError(e)?e.response?.data?.detail??'保存失败':'保存失败')}}
  const orderColumns=[
    {title:'申请编号',dataIndex:'application_no',render:(v:string)=><strong>{v}</strong>},
    {title:'企业主体',dataIndex:'company_name',render:(v?:string)=>v||'未填写'},
    {title:'国家',dataIndex:'country'},{title:'服务',dataIndex:'service_type'},
    {title:'注册号',dataIndex:'registration_number',render:(v?:string)=>v||'--'},
    {title:'服务进度',dataIndex:'status',render:(v:ApplicationStatus)=><Tag color={statusMeta[v].color}>{statusMeta[v].text}</Tag>},
    {title:'提交时间',dataIndex:'submitted_time',render:(v?:string)=>v?dayjs(v).format('YYYY-MM-DD HH:mm'):'--'},
    {title:'操作',render:(_:unknown,r:Application)=><Button type="link" icon={<EyeOutlined/>} disabled={r.status==='DRAFT'} onClick={()=>navigate(`/applications/${r.id}`)}>{r.status==='DRAFT'?'尚未提交':'查看递单'}</Button>},
  ]
  const companyColumns=[
    {title:'企业名称',dataIndex:'company_name',render:(v:string,r:CustomerCompany)=><div><strong>{v}</strong>{r.company_name_en&&<div className="muted">{r.company_name_en}</div>}</div>},
    {title:'注册地',dataIndex:'registration_region',render:(v?:string)=>v?regions[v]||v:'--'},
    {title:'企业类型',dataIndex:'company_type',render:(v?:string)=>v||'--'},
    {title:'营业执照号 / 企业注册号',dataIndex:'register_number',render:(v?:string)=>v||'--'},
    {title:'资料完整度',dataIndex:'completeness',render:(v:number)=><Progress percent={v} size="small" style={{width:120}}/>},
    {title:'关联递单',dataIndex:'application_count',render:(v:number,r:CustomerCompany)=><Button type="link" onClick={()=>{const order=detail?.applications.find(item=>item.company_name===r.company_name);if(order)navigate(`/applications/${order.id}`)}}>{v} 份</Button>},
  ]
  return <PageContainer title={isAgent?'代理管理':'直客管理'} subTitle={isAgent?'查看代理账号、企业主体及其全部递单':'查看直客账号、企业主体及其全部递单'} extra={isAdmin?<Button type="primary" icon={<PlusOutlined/>} onClick={create}>新增{isAgent?'代理':'直客'}</Button>:undefined}>
    <Table<CustomerAccount> rowKey="id" loading={loading} dataSource={items} columns={[
      {title:isAgent?'代理名':'直客名称',dataIndex:'name',render:(v,r)=><Button type="link" style={{padding:0,fontWeight:600}} onClick={()=>void showDetail(r)}>{v}</Button>},
      {title:'登录账号',dataIndex:'username'},
      {title:'联系邮箱',dataIndex:'email',render:(v?:string)=>v||'—'},
      {title:'联系人',render:(_,r)=><>{r.contact_name||'—'}<div className="muted">{r.contact_phone}</div></>},
      {title:'订单数量',dataIndex:'order_count',render:(v,r)=><Button type="link" onClick={()=>void showDetail(r)}>{v} 份</Button>},
      {title:'企业主体',dataIndex:'company_count',render:(v,r)=><Button type="link" onClick={()=>void showDetail(r)}>{v} 个</Button>},
      {title:'状态',render:(_,r)=><Tag color={r.active?'success':'default'}>{r.active?'启用':'停用'}</Tag>},
      {title:'操作',render:(_,r)=><Space><Button type="link" icon={<EyeOutlined/>} onClick={()=>void showDetail(r)}>查看</Button>{isAdmin&&<Button type="link" onClick={()=>edit(r)}>编辑</Button>}</Space>},
    ]}/>
    <Modal title={`${editing?'编辑':'新增'}${isAgent?'代理':'直客'}`} open={open} onCancel={()=>setOpen(false)} onOk={()=>void save()} destroyOnHidden><Form form={form} layout="vertical"><Form.Item name="name" label={isAgent?'代理名':'直客名称'} rules={[{required:true,message:'请填写名称'}]}><Input/></Form.Item>{!editing&&<Form.Item name="username" label="登录用户名" rules={[{required:true},{min:3}]}><Input/></Form.Item>}<Form.Item name="email" label="联系邮箱" extra="订单状态、补件要求和下证资料更新将发送至此邮箱" rules={[{required:true,message:'请填写联系邮箱'},{type:'email',message:'请输入有效邮箱'}]}><Input/></Form.Item>{!editing&&<Form.Item name="password" label="初始密码" rules={[{required:true},{min:6}]}><Input.Password/></Form.Item>}<Form.Item name="contact_name" label="联系人"><Input/></Form.Item><Form.Item name="contact_phone" label="联系电话"><Input/></Form.Item>{editing&&<Form.Item name="active" label="账号状态" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用"/></Form.Item>}</Form></Modal>
    <Modal title={`${detail?.account.name||''} · 账号详情`} width={1180} open={Boolean(detail)||detailLoading} loading={detailLoading} onCancel={()=>setDetail(undefined)} footer={<Button onClick={()=>setDetail(undefined)}>关闭</Button>}>
      {detail&&<><Descriptions bordered size="small" column={3}><Descriptions.Item label="客户类型">{detail.account.customer_type==='AGENT'?'代理':'直客'}</Descriptions.Item><Descriptions.Item label="登录账号">{detail.account.username}</Descriptions.Item><Descriptions.Item label="联系邮箱">{detail.account.email||'--'}</Descriptions.Item><Descriptions.Item label="联系人">{detail.account.contact_name||'--'}</Descriptions.Item><Descriptions.Item label="联系电话">{detail.account.contact_phone||'--'}</Descriptions.Item><Descriptions.Item label="账号状态"><Tag color={detail.account.active?'success':'default'}>{detail.account.active?'启用':'停用'}</Tag></Descriptions.Item></Descriptions><Row gutter={16} style={{margin:'18px 0'}}><Col span={8}><Card><Statistic title="订单总数" value={detail.applications.length} prefix={<FileTextOutlined/>}/></Card></Col><Col span={8}><Card><Statistic title="企业主体" value={detail.companies.length} prefix={<ApartmentOutlined/>}/></Card></Col><Col span={8}><Card><Statistic title="已完成订单" value={detail.applications.filter(item=>item.status==='COMPLETED').length}/></Card></Col></Row><Tabs items={[{key:'orders',label:`订单信息（${detail.applications.length}）`,children:<Table rowKey="id" dataSource={detail.applications} columns={orderColumns} pagination={{pageSize:8}}/>},{key:'companies',label:`企业主体（${detail.companies.length}）`,children:<Table rowKey="id" dataSource={detail.companies} columns={companyColumns} pagination={{pageSize:8}}/>}]}/></>}
    </Modal>
  </PageContainer>
}
