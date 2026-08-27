export interface ColumnInfo {
	name: string;
	dtype: string;
}

export interface Dataset {
	id: number;
	original_filename: string;
	file_format: string;
	file_size_bytes: number;
	row_count: number;
	column_count: number;
	columns: ColumnInfo[];
	status: string;
	created_at: string;
	updated_at: string;
}

export interface PreviewResponse {
	dataset: Dataset;
	rows: Record<string, unknown>[];
	total_rows_shown: number;
}

export interface NumericStats {
	count: number | null;
	mean: number | null;
	median: number | null;
	min: number | null;
	max: number | null;
	sum: number | null;
	std: number | null;
}

export interface ColumnStatistics {
	name: string;
	dtype: string;
	count: number;
	missing: number;
	missing_percent: number;
	unique: number;
	numeric: NumericStats | null;
}

export interface StatisticsResponse {
	dataset_id: number;
	columns: ColumnStatistics[];
}

export interface QualityIssue {
	type: string;
	severity: string;
	message: string;
	affected_columns: string[];
}

export interface QualityResponse {
	dataset_id: number;
	total_rows: number;
	total_columns: number;
	total_cells: number;
	missing_cells: number;
	missing_percent: number;
	duplicate_rows: number;
	empty_columns: string[];
	columns: ColumnStatistics[];
	issues: QualityIssue[];
}

export interface ChartDataset {
	label: string;
	data: (number | { x: number; y: number })[];
}

export interface ChartSpec {
	type: 'bar' | 'line' | 'pie' | 'doughnut' | 'scatter' | 'histogram';
	title: string;
	labels: string[];
	datasets: ChartDataset[];
}

export interface AskResponse {
	analysis_id: number;
	question: string;
	answer: string;
	analysis_type: string;
	results: Record<string, unknown> | null;
	chart_spec: ChartSpec | null;
	created_at: string;
}

export interface Analysis {
	id: number;
	dataset_id: number;
	question: string;
	answer: string;
	analysis_type: string;
	results: Record<string, unknown> | null;
	chart_spec: ChartSpec | null;
	created_at: string;
}

export interface CleanResponse {
	dataset_id: number;
	message: string;
	rows_before: number;
	rows_after: number;
	columns_before: number;
	columns_after: number;
	operations: string[];
}

export interface Report {
	id: number;
	dataset_id: number;
	report_name: string;
	created_at: string;
}
