export type ApplicationStatus = 'DRAFT' | 'SUBMITTED' | 'REVIEWING' | 'NEED_FIX' | 'REGISTERING' | 'COMPLETED'

export interface User {
  id: number
  username: string
  phone?: string
  email?: string
  role: 'CUSTOMER' | 'STAFF' | 'ADMIN'
}

export interface Application {
  id: number
  application_no: string
  purchase_order_id?: number
  instance_index?: number
  company_name?: string
  registration_number?: string
  certificate_file?: string
  invoice_file?: string
  result_file?: string
  service_expiry_date?: string
  country: string
  service_type: string
  status: ApplicationStatus
  created_time: string
  submitted_time?: string
  reviewed_time?: string
  review_note?: string
  delivery_stage?: 'RECEIVED' | 'PROVIDER_SUBMITTED' | 'SUPPLEMENT_FOLLOW_UP' | 'COUNTERSIGN_PENDING' | 'COUNTERSIGNED' | 'COMPLETED'
  countersign_note?: string
  countersign_file?: string
  countersign_required: boolean
}

export interface ApplicationList {
  items: Application[]
  total: number
  page: number
  page_size: number
}

export interface ServiceOption { value: string; label: string; description: string }
export interface CountryOption { value: string; label: string; services: ServiceOption[] }

export interface DynamicField {
  id: number; field_name: string; label: string; field_type: 'text' | 'number' | 'select' | 'date' | 'upload'
  required: boolean; options?: string[]; sort: number
}
export interface MaterialRequirement { id: number; material_name: string; required: boolean; file_type: string; description: string; sort: number }
export interface ServiceTemplate { id: number; country: string; service_type: string; version: number; fields: DynamicField[]; materials: MaterialRequirement[] }
export interface LegalPerson { name_cn?: string; name_en?: string; certificate_type?: string; certificate_number?: string; gender?: string; contact_email?: string; contact_phone?: string; front_file?: string; back_file?: string; signature_file?: string }
export interface Company { id?: number; company_name: string; company_name_en?: string; registration_region?: string; company_type?: string; register_number?: string; established_date?: string; vat_number?: string; register_address?: string; license_file?: string; license_translation_file?: string; credit_report_file?: string; br_file?: string; cr_file?: string; nnc1_file?: string; director_index_file?: string; created_time?: string; legal_person?: LegalPerson }
export interface CompanyProfile extends Company { id: number; application_count: number; completeness: number; last_application_time?: string }
export interface Store { platform?: string; store_url?: string; store_name?: string; company_name_en?: string; register_city_en?: string; postal_code?: string; register_address_en?: string; screenshot_file?: string }
export interface Product { id?: number; product_data: Record<string, string | number | undefined> }
export interface MaterialFile { id: number; requirement_id: number; file_url: string; original_name: string; file_size: number; upload_time: string; auto_synced?: boolean }
export type RecognizableDocumentType = 'business_license' | 'id_card_front' | 'passport'
export interface RecognizedField { target_field: string; label: string; value: string; confidence: number }
export interface DocumentRecognition { document_type: RecognizableDocumentType; fields: RecognizedField[]; warnings: string[] }
export interface ApplicationFormData { application: Application; template: ServiceTemplate; company?: Company; store?: Store; products: Product[]; material_files: MaterialFile[] }
export interface StatusHistory { id: number; from_status: string; to_status: string; note?: string; operator_name: string; created_time: string }

export interface ProductCategorySelection { category:string; brands:string[] }
export interface PortalCatalogService { id: string; country: string; country_code: string; product_type: string; service_type: string; title: string; description: string; price: number; additional_category_price:number; additional_brand_price:number; unit: string; color: string; reporting_frequency: string; service_years: string[]; subject_types: string[]; package_types: string[]; product_categories:string[]; purchase_notes: string[] }
export interface PortalTodo { id: string; type: 'MATERIAL' | 'RENEWAL' | 'COUNTERSIGN'; company: string; country: string; service: string; service_no: string; created_time: string; application_id?: number; order_id?:number }
export interface PortalDashboard { pending_materials: number; pending_renewals: number; pending_countersigns:number; unread_messages: number; todos: PortalTodo[] }
export interface PortalMessage { id: string; title: string; description: string; message_type: string; created_time: string; read: boolean; application_id?: number }
export interface Manager { name: string; role: string; phone: string; wechat: string; work_hours: string; online: boolean }
export interface CartItem { id: number; service: PortalCatalogService; service_year:string; package_type:string; product_configurations:ProductCategorySelection[]; quantity: number; created_time: string }
export type PurchaseOrderStatus = 'PENDING' | 'PAYMENT_CONFIRMING' | 'PAID' | 'CANCELLED' | 'PAYMENT_FAILED' | 'PARTIALLY_REFUNDED' | 'REFUNDED'
export interface ServiceInstance {
  id: number
  application_no: string
  instance_index: number
  company_name?: string
  status: ApplicationStatus
  registration_number?: string
  certificate_file?: string
  invoice_file?: string
  result_file?: string
  service_expiry_date?: string
  delivery_stage?: 'RECEIVED' | 'PROVIDER_SUBMITTED' | 'SUPPLEMENT_FOLLOW_UP' | 'COUNTERSIGN_PENDING' | 'COUNTERSIGNED' | 'COMPLETED'
  countersign_note?: string
  countersign_file?: string
  countersign_required: boolean
}
export interface PurchaseOrder {
  id: number
  order_no: string
  service: PortalCatalogService
  service_year: string
  subject_type: string
  package_type: string
  product_configurations: ProductCategorySelection[]
  quantity: number
  unit_price: number
  batch_no?: string
  standard_amount: number
  discount_amount: number
  discount_reason?: string
  total_amount: number
  status: PurchaseOrderStatus
  payment_method?: 'OFFLINE'
  payer_name?: string
  payment_proof?: string
  actual_paid_amount?: number
  finance_receipt?: string
  finance_note?: string
  contract_no?: string
  contract_file?: string
  contract_version?: string
  customer_signed_contract_file?: string
  signed_contract_uploaded_time?: string
  application_id?: number
  service_instances: ServiceInstance[]
  service_progress?: ApplicationStatus
  created_time: string
  paid_time?: string
}
