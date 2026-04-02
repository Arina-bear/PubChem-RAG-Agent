export type ApiSource = "pubchem-pug-rest" | "pubchem-pug-view" | "interpreter" | "mixed";

export type ManualInputMode = "cid" | "name" | "smiles" | "inchikey" | "formula";
export type ManualOperation =
  | "property"
  | "record"
  | "synonyms"
  | "description"
  | "xrefs"
  | "assaysummary"
  | "image"
  | "pug_view_overview"
  | "safety"
  | "fastformula"
  | "fastidentity"
  | "fastsimilarity_2d"
  | "fastsubstructure";

export interface WarningMessage {
  code: string;
  message: string;
}

export interface PresentationHints {
  active_tab: string;
  available_tabs: string[];
}

export interface ErrorPayload {
  code: string;
  message: string;
  retriable: boolean;
  details?: Record<string, unknown> | null;
}

export interface CompoundMatchCard {
  cid: number;
  title?: string | null;
  molecular_formula?: string | null;
  molecular_weight?: number | null;
  image_data_url?: string | null;
}

export interface CompoundOverview extends CompoundMatchCard {
  iupac_name?: string | null;
  exact_mass?: number | null;
  canonical_smiles?: string | null;
  inchi_key?: string | null;
  xlogp?: number | null;
  tpsa?: number | null;
  synonyms_preview: string[];
}

export interface PaginationSpec {
  start: number;
  limit: number;
}

export interface ManualQuerySpec {
  domain: "compound";
  input_mode: ManualInputMode;
  identifier: string;
  operation: ManualOperation;
  properties: string[];
  filters: Record<string, unknown>;
  pagination: PaginationSpec | null;
  output: "json";
  include_raw: boolean;
}

export interface ResolvedQuery {
  domain: "compound";
  input_mode: ManualInputMode;
  identifier: string;
  operation: ManualOperation;
}

export interface QueryNormalizedPayload {
  query: ResolvedQuery;
  matches: CompoundMatchCard[];
  primary_result: CompoundOverview | null;
  synonyms: string[];
}

export interface QueryResponseEnvelope {
  trace_id: string;
  source: ApiSource;
  status: "success" | "error";
  raw: Record<string, unknown> | null;
  normalized: QueryNormalizedPayload | null;
  presentation_hints: PresentationHints;
  warnings: WarningMessage[];
  error: ErrorPayload | null;
}

export interface InterpretRequest {
  text: string;
}

export interface InterpretationCandidate {
  label: string;
  rationale: string;
  confidence: number;
  query: ManualQuerySpec;
}

export interface InterpretationPayload {
  candidates: InterpretationCandidate[];
  confidence: number;
  ambiguities: string[];
  assumptions: string[];
  warnings: string[];
  needs_confirmation: boolean;
  recommended_candidate_index: number | null;
}

export interface InterpretResponseEnvelope {
  trace_id: string;
  source: string;
  status: string;
  raw: Record<string, unknown> | null;
  normalized: InterpretationPayload | null;
  presentation_hints: PresentationHints;
  warnings: WarningMessage[];
  error: ErrorPayload | null;
}

export type LLMProviderName = "openai" | "modal_glm";
export type AgentSearchMode = "name" | "smiles" | "formula" | "mass_range" | "clarify";

export interface AgentRequest {
  text: string;
  provider?: LLMProviderName | null;
  model?: string | null;
  max_steps?: number;
  max_output_tokens?: number;
  include_raw?: boolean;
}

export interface AgentToolCallTrace {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "success" | "error";
  result: Record<string, unknown> | unknown[] | string | null;
  error_message?: string | null;
}

export interface AgentParsedQuery {
  compound_name?: string | null;
  synonyms: string[];
  smiles?: string | null;
  formula?: string | null;
  mass_range?: [number, number] | null;
  mass_type?: "molecular_weight" | "exact_mass" | "monoisotopic_mass" | null;
  language: "ru" | "en" | "unknown";
  normalized_language: "en";
  confidence: number;
  ambiguities: string[];
  recommended_search_mode: AgentSearchMode;
}

export interface AgentNormalizedPayload {
  user_text: string;
  answer: string;
  provider: LLMProviderName;
  model: string;
  parsed_query: AgentParsedQuery;
  needs_clarification: boolean;
  clarification_question?: string | null;
  compounds: CompoundOverview[];
  tool_calls: AgentToolCallTrace[];
}

export interface AgentResponseEnvelope {
  trace_id: string;
  source: "llm-agent";
  status: "success" | "needs_clarification" | "error";
  raw: Record<string, unknown> | null;
  normalized: AgentNormalizedPayload | null;
  presentation_hints: PresentationHints;
  warnings: WarningMessage[];
  error: ErrorPayload | null;
}

export interface ApiRequestResult<T> {
  ok: boolean;
  status: number;
  data: T;
}
