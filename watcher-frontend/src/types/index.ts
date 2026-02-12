// Export all types from a central location
export * from './search'
export * from './boletines'
export * from './actos'
export * from './alertas'
export * from './metricas'
export * from './presupuesto'

// Common types
export interface ApiError {
  detail: string;
  status?: number;
}

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}
