export interface Acto {
  id: number;
  tipo_acto: string;
  numero?: string;
  fecha?: string;
  organismo: string;
  beneficiario?: string;
  monto?: number;
  partida?: string;
  descripcion: string;
  nivel_riesgo: 'ALTO' | 'MEDIO' | 'BAJO';
  created_at: string;
  keywords?: string;
}

export interface Vinculo {
  id: number;
  acto_id: number;
  programa_id: number;
  score_confianza: number;
  metodo_matching: string;
  detalles_json?: Record<string, unknown>;
  programa?: {
    id: number;
    organismo: string;
    programa: string;
    descripcion: string;
    monto_vigente: number;
  };
}

export interface ActoDetail extends Acto {
  vinculos: Vinculo[];
  fragmento_original: string;
  pagina?: number;
}

export interface ActosFilters {
  skip?: number;
  limit?: number;
  tipo_acto?: string;
  organismo?: string;
  nivel_riesgo?: string;
}

export interface ActosListResponse {
  actos: Acto[];
  total: number;
  page: number;
  page_size: number;
}
