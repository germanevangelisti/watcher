// Tipos para gestión de documentos/boletines

// Backend response structure
export interface BoletinBackend {
  id: number;
  filename: string;
  date: string;  // Format: "YYYYMMDD"
  section: string;
  status: string;  // "completed", "pending", "failed"
  has_file: boolean;
  file_path: string | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  fuente: string;
  jurisdiccion_id: number;
  jurisdiccion_nombre: string;
  seccion_nombre: string;
}

// Frontend normalized structure
export interface Boletin {
  id: number;
  filename: string;
  date: string;
  year: number;
  month: number;
  section: string;
  pdf_path?: string;
  txt_path?: string;
  processed: boolean;
  has_file: boolean;
  processing_date?: string;
  total_pages?: number;
  file_hash?: string;
  created_at: string;
  updated_at?: string;
  status?: string;
  fuente?: string;
  jurisdiccion_nombre?: string;
  seccion_nombre?: string;
}

export interface BoletinDetail extends Boletin {
  chunks_count: number;
  entities_count: number;
  content_preview?: string;
}

export interface BoletinesFilters {
  skip?: number;
  limit?: number;
  year?: number;
  month?: number;
  section?: string;
  processed?: boolean;
  has_file?: boolean;
}

export interface BoletinesListResponse {
  boletines: Boletin[];
  total: number;
  page: number;
  page_size: number;
}

export interface UploadBoletinRequest {
  file: File;
  metadata?: {
    section?: string;
    year?: number;
    month?: number;
  };
}

export interface UploadBoletinResponse {
  success: boolean;
  boletin_id: number;
  filename: string;
  message: string;
}
