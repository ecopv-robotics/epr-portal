import type { Application } from './types'

type ProgressSource = Pick<Application, 'status' | 'delivery_stage'>

/** Customer milestones deliberately omit internal assignment and supplement handling. */
export function customerProgress(application: ProgressSource) {
  const { status, delivery_stage: stage } = application
  const rejected = status === 'NEED_FIX'
  const reviewed = status === 'REGISTERING' || status === 'COMPLETED'
  const submittedToProvider = reviewed && Boolean(stage && stage !== 'RECEIVED')
  const signed = reviewed && (stage === 'COUNTERSIGNED' || status === 'COMPLETED')
  const issued = status === 'COMPLETED'
  const current = issued ? 6 : signed ? 4 : stage === 'COUNTERSIGN_PENDING' && reviewed ? 3
    : reviewed ? 2 : status === 'DRAFT' ? 0 : 1
  const label = issued ? '待确认交付' : signed ? '待下证' : current === 3 ? '待二次回签'
    : reviewed ? submittedToProvider ? '已提交服务商' : '待提交服务商'
      : rejected ? '驳回修改' : status === 'DRAFT' ? '待提交资料' : '待审核'
  const description = issued ? '注册结果已更新，请在「注册信息」中查看注册号、证书及交付文件。'
    : signed ? '回签环节已完成，正在等待官方下证。'
      : current === 3 ? '请按回签要求签署文件，并上传二次回签 PDF。'
        : reviewed ? submittedToProvider ? '资料已提交服务商办理，若需要二次回签，会在此通知你。' : '资料已审核通过，正在安排提交服务商。'
          : rejected ? '资料审核未通过，请根据审核意见修改后重新提交。'
            : status === 'DRAFT' ? '请完善公司、法人、店铺和产品资料后提交审核。' : '资料已提交，正在等待审核结果。'
  return {
    current, label, description, rejected,
    color: rejected || current === 3 || issued ? 'warning' : 'processing',
    items: [
      { title: status === 'DRAFT' ? '待提交资料' : '已提交资料' },
      { title: rejected ? '驳回修改' : reviewed ? '已审核' : '待审核' },
      { title: '提交服务商', description: submittedToProvider ? '已提交' : undefined },
      { title: '二次回签', description: signed ? '已完成' : current === 3 ? '待你回签' : undefined },
      { title: '待下证', description: issued ? '已完成' : undefined },
      { title: '已下证' },
      { title: '待确认交付' },
    ],
  }
}
