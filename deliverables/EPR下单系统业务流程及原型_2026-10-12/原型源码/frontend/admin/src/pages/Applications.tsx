import { EyeOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Tag } from 'antd';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import type { Application, ApplicationList, ApplicationStatus } from '../types';

const meta:Record<ApplicationStatus,{text:string;color:string}>={DRAFT:{text:'草稿',color:'default'},SUBMITTED:{text:'待接单',color:'blue'},REVIEWING:{text:'审核中',color:'processing'},NEED_FIX:{text:'待补件',color:'warning'},REGISTERING:{text:'注册中',color:'cyan'},COMPLETED:{text:'已完成',color:'success'}};

export default function Applications(){
  const nav=useNavigate();
  const columns:ProColumns<Application>[]=[
    {title:'申请编号',dataIndex:'application_no',copyable:true},
    {title:'客户公司',dataIndex:'company_name',search:false,renderText:v=>v||'未填写'},
    {title:'代理名',dataIndex:'agent_name',search:false,render:(_,r)=>r.agent_name?<Tag color="purple">{r.agent_name}</Tag>:'—'},
    {title:'国家',dataIndex:'country',search:false},
    {title:'服务',dataIndex:'service_type',search:false},
    {title:'状态',dataIndex:'status',valueType:'select',valueEnum:Object.fromEntries(Object.entries(meta).map(([k,v])=>[k,{text:v.text,status:k==='COMPLETED'?'Success':undefined}])),render:(_,r)=><Tag color={meta[r.status].color}>{meta[r.status].text}</Tag>},
    {title:'提交时间',dataIndex:'submitted_time',search:false,renderText:v=>v?dayjs(v).format('YYYY-MM-DD HH:mm'):'—'},
    {title:'操作',valueType:'option',render:(_,r)=>{const reviewable=r.status==='SUBMITTED'||r.status==='REVIEWING';return <Button type="link" icon={<EyeOutlined/>} onClick={()=>nav(`/applications/${r.id}`)}>{reviewable?'审核':'查看'}</Button>}},
  ];
  return <PageContainer title="递单管理" subTitle="查询、分配和审核客户申请"><ProTable<Application> rowKey="id" columns={columns} request={async(params)=>{const {data}=await api.get<ApplicationList>('/admin/applications',{params:{page:params.current,page_size:params.pageSize,keyword:params.application_no,status:params.status}});return {data:data.items,total:data.total,success:true}}} pagination={{defaultPageSize:20,showSizeChanger:true}} search={{labelWidth:'auto'}}/></PageContainer>;
}
