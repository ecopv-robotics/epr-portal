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
export interface ApplicationFormData { application: Application; template: ServiceTemplate; company?: Company; store?: Store; products: Product[]; material_files: MaterialFile[] }
export interface StatusHistory { id: number; from_status: string; to_status: string; note?: string; operator_name: string; created_time: string }
