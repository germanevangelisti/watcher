// Types for the Adversarial Verification system (Phases I-V)

export type ClaimType =
  | "subject"
  | "action"
  | "reference"
  | "amount"
  | "temporal"
  | "relationship"
  | "evidence_anchor";

export type VerificationStatus =
  | "verified"
  | "unverifiable"
  | "contradicted"
  | "pending";

export interface AIU {
  claim_type: ClaimType;
  claim_text: string;
  verification_status: VerificationStatus;
  confidence: number;
  source_output_id?: string;
  evidence?: string;
}

export interface AIUSummary {
  total_aius: number;
  by_type: Record<ClaimType, number>;
}

export interface ReferenceResult {
  text: string;
  ref_type: string;
  normalized: string;
  status: "verified" | "not_found" | "unverifiable";
  evidence?: string;
}

export interface FirewallValidation {
  references: ReferenceResult[];
  verified_count: number;
  not_found_count: number;
  unverifiable_count: number;
  firewall_score: number;
  flagged: boolean;
}

export interface VCPMetrics {
  vcp_score: number;
  total_aius: number;
  verified: number;
  unverifiable: number;
  contradicted: number;
  requires_attention: boolean;
  boletin_id?: number;
  latency_p50_ms?: number;
  latency_p95_ms?: number;
  sample_count: number;
}

export interface VerificationResult {
  vcp_score: number;
  verified_aius: number;
  unverifiable_aius: number;
  contradicted_aius: number;
  requires_human_review: boolean;
  aiu_details: AIU[];
}
