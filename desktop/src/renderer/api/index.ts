import api from './client';

// ===== Types =====

export interface ViolationItem {
  type: string;
  type_label: string;
  content: string;
  regulation: string;
  regulation_detail: string;
  severity: string;
  severity_label: string;
  suggestion: string;
  score: number;
}

export interface CheckRequest {
  description: string;
  category: string;
  market: string;
}

export interface CheckResponse {
  report_id: string;
  risk_score: number;
  risk_level: string;
  risk_description: string;
  market: string;
  category: string;
  violations: ViolationItem[];
  compliant_version: string;
  required_labels: string[];
  required_certifications: string[];
  suggestions: string[];
}

export interface BatchCheckRequest {
  items: CheckRequest[];
}

export interface BatchCheckResponse {
  results: CheckResponse[];
  total: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
}

export interface MarketResponse {
  code: string;
  name: string;
  categories: string[];
}

export interface LabelResponse {
  market: string;
  category: string;
  labels: string[];
}

export interface CertificationResponse {
  market: string;
  category: string;
  certifications: string[];
}

export interface ReportItem {
  id: string;
  category: string;
  market: string;
  risk_score: number;
  risk_level: string;
  violation_count: number;
  created_at: string;
}

export interface ReportListResponse {
  items: ReportItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReportDetailResponse {
  id: string;
  description: string;
  result: CheckResponse;
  created_at: string;
}

// ===== API Functions =====

export async function checkCompliance(request: CheckRequest): Promise<CheckResponse> {
  const { data } = await api.post<CheckResponse>('/check', request);
  return data;
}

export async function batchCheckCompliance(request: BatchCheckRequest): Promise<BatchCheckResponse> {
  const { data } = await api.post<BatchCheckResponse>('/check/batch', request);
  return data;
}

export async function getMarkets(): Promise<MarketResponse[]> {
  const { data } = await api.get<MarketResponse[]>('/markets');
  return data;
}

export async function getCategories(market: string): Promise<string[]> {
  const { data } = await api.get<{ name: string }[]>(`/markets/${market}/categories`);
  return data.map((d) => d.name);
}

export async function getLabels(market: string, category: string): Promise<LabelResponse> {
  const { data } = await api.get<LabelResponse>('/labels', { params: { market, category } });
  return data;
}

export async function getCertifications(market: string, category: string): Promise<CertificationResponse> {
  const { data } = await api.get<CertificationResponse>('/certifications', { params: { market, category } });
  return data;
}

export async function getReports(params: {
  page?: number;
  page_size?: number;
  market?: string;
  category?: string;
  risk_level?: string;
}): Promise<ReportListResponse> {
  const { data } = await api.get<ReportListResponse>('/reports', { params });
  return data;
}

export async function getReportDetail(reportId: string): Promise<ReportDetailResponse> {
  const { data } = await api.get<ReportDetailResponse>(`/reports/${reportId}`);
  return data;
}

export async function deleteReport(reportId: string): Promise<void> {
  await api.delete(`/reports/${reportId}`);
}

// ===== Image Check =====

export async function checkImage(file: File, category: string, market: string): Promise<CheckResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);
  formData.append('market', market);
  const { data } = await api.post<CheckResponse>('/check/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
  return data;
}

// ===== Auth =====

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface UserInfo {
  id: string;
  username: string;
  role: string;
}

export async function login(request: LoginRequest): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', request);
  return data;
}

// ===== Report Export =====

export async function exportReportPdf(reportId: string): Promise<Blob> {
  const { data } = await api.get(`/reports/${reportId}/export/pdf`, {
    responseType: 'blob',
  });
  return data;
}

// ===== Feedback (Data Flywheel) =====

export interface FeedbackRequest {
  report_id: string;
  feedback_type: 'false_positive' | 'false_negative' | 'correct';
  violation_type: string;
  violation_content: string;
  user_comment?: string;
  market: string;
  category: string;
  original_description?: string;
  risk_score?: number;
}

export interface FeedbackResponse {
  id: string;
  report_id: string;
  feedback_type: string;
  violation_type: string;
  violation_content: string;
  user_comment: string;
  created_at: string;
}

export async function submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
  const { data } = await api.post<FeedbackResponse>('/feedback', request);
  return data;
}

export interface AccuracyMetrics {
  total_feedbacks: number;
  false_positive_count: number;
  false_negative_count: number;
  correct_count: number;
  false_positive_rate: number;
  false_negative_rate: number;
  accuracy: number;
  by_violation_type: Record<string, {
    total: number;
    fp: number;
    fn: number;
    correct: number;
    accuracy: number;
    fp_rate: number;
    fn_rate: number;
  }>;
}

export async function getAccuracyMetrics(): Promise<AccuracyMetrics> {
  const { data } = await api.get<AccuracyMetrics>('/feedback/accuracy');
  return data;
}

// ===== Platform & Patrol =====

export interface PlatformStatus {
  platform: string;
  status: string;
}

export async function getPlatformStatus(): Promise<PlatformStatus[]> {
  const { data } = await api.get<PlatformStatus[]>('/platforms');
  return data;
}

export interface PatrolRequest {
  platform: string;
  market: string;
  category?: string;
  limit?: number;
}

export async function triggerPatrol(request: PatrolRequest): Promise<unknown> {
  const { data } = await api.post('/patrol', request, { timeout: 120000 });
  return data;
}

// ===== Dashboard & Patrol History =====

export interface DashboardStatsResponse {
  weekly_volume: { date: string; count: number }[];
  violation_type_distribution: Record<string, number>;
  risk_score_trend: { date: string; avg_score: number }[];
  total_reports: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
}

export async function getDashboardStats(): Promise<DashboardStatsResponse> {
  const { data } = await api.get<DashboardStatsResponse>('/dashboard/stats');
  return data;
}

export interface PatrolSummary {
  id: string;
  patrol_time: string;
  platform: string;
  market: string;
  total_listings: number;
  checked_listings: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  compliant_count: number;
  alert_count: number;
}

export async function getPatrolHistory(params?: { platform?: string; limit?: number }): Promise<PatrolSummary[]> {
  const { data } = await api.get<PatrolSummary[]>('/patrol/history', { params });
  return data;
}

// ===== LLM Configuration =====

export interface LLMProviderInfo {
  id: string;
  name: string;
  default_api_base: string;
  default_model: string;
  models: string[];
  requires_api_key: boolean;
}

export interface LLMConfigRequest {
  provider: string;
  api_key: string;
  api_base: string;
  model: string;
  max_tokens?: number;
  temperature?: number;
}

export interface LLMConfigResponse {
  provider: string;
  api_key_masked: string;
  api_base: string;
  model: string;
  max_tokens: number;
  temperature: number;
  is_active: boolean;
  updated_at: string;
}

export interface LLMTestRequest {
  provider: string;
  api_key: string;
  api_base: string;
  model: string;
  max_tokens?: number;
  temperature?: number;
}

export interface LLMTestResponse {
  success: boolean;
  message: string;
  latency_ms?: number;
  model_info?: string;
}

export async function getLLMProviders(): Promise<LLMProviderInfo[]> {
  const { data } = await api.get<LLMProviderInfo[]>('/llm/providers');
  return data;
}

export async function getLLMConfig(): Promise<LLMConfigResponse> {
  const { data } = await api.get<LLMConfigResponse>('/llm/config');
  return data;
}

export async function saveLLMConfig(config: LLMConfigRequest): Promise<LLMConfigResponse> {
  const { data } = await api.put<LLMConfigResponse>('/llm/config', config);
  return data;
}

export async function deleteLLMConfig(): Promise<void> {
  await api.delete('/llm/config');
}

export async function testLLMConnection(request: LLMTestRequest): Promise<LLMTestResponse> {
  const { data } = await api.post<LLMTestResponse>('/llm/test', request);
  return data;
}

// ===== Comparison Mode =====

export interface ComparisonResult {
  risk_score: number;
  risk_level: string;
  risk_description: string;
  violations: ViolationItem[];
  violation_count: number;
  compliant_version: string;
}

export interface ComparisonCheckResponse {
  report_id: string;
  description: string;
  market: string;
  category: string;
  keyword_result: ComparisonResult;
  ai_result: ComparisonResult | null;
  hybrid_result: ComparisonResult;
  required_labels: string[];
  required_certifications: string[];
  suggestions: string[];
}

export async function checkComparison(request: CheckRequest): Promise<ComparisonCheckResponse> {
  const { data } = await api.post<ComparisonCheckResponse>('/check/comparison', request);
  return data;
}

// ===== Multi-Market Comparison (Demo Mode) =====

export interface MultiMarketResult {
  market: string;
  market_name: string;
  risk_score: number;
  risk_level: string;
  risk_description: string;
  violations: ViolationItem[];
  violation_count: number;
  compliant_version: string;
  required_labels: string[];
  required_certifications: string[];
  suggestions: string[];
}

export interface MultiMarketCheckResponse {
  description: string;
  category: string;
  results: MultiMarketResult[];
  best_market: string;
  worst_market: string;
}

export async function checkMultiMarket(request: CheckRequest): Promise<MultiMarketCheckResponse> {
  const { data } = await api.post<MultiMarketCheckResponse>('/check/multi-market', request);
  return data;
}

// ===== Multi-LLM Comparison =====

export interface LLMComparisonResult {
  provider: string;
  provider_name: string;
  model: string;
  risk_score: number;
  risk_level: string;
  violations: ViolationItem[];
  violation_count: number;
  latency_ms: number | null;
}

export interface LLMComparisonRequest {
  description: string;
  category: string;
  market: string;
  providers: string[];
}

export interface LLMComparisonResponse {
  description: string;
  category: string;
  market: string;
  results: LLMComparisonResult[];
}

export async function checkLLMComparison(request: LLMComparisonRequest): Promise<LLMComparisonResponse> {
  const { data } = await api.post<LLMComparisonResponse>('/check/llm-comparison', request);
  return data;
}

// ===== Cost Savings Calculator =====

export interface PenaltyEstimate {
  market: string;
  market_label: string;
  min_penalty: number;
  max_penalty: number;
  currency: string;
  estimated_penalty: number;
  violation_count: number;
  risk_level: string;
}

export interface CostEstimateItem {
  scenario: string;
  estimated_loss: number;
  probability: number;
  expected_loss: number;
  source: string;
}

export interface CostSavingsResponse {
  total_risk_exposure: number;
  annual_check_cost: number;
  annual_savings: number;
  savings_per_check: number;
  market_penalties: PenaltyEstimate[];
  case_losses: CostEstimateItem[];
  disclaimer: string;
}

export async function getCostSavings(): Promise<CostSavingsResponse> {
  const { data } = await api.get<CostSavingsResponse>('/compliance/cost-savings');
  return data;
}
