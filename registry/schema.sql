CREATE TABLE schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE ingest_runs(ingest_run_id TEXT PRIMARY KEY,started_at_utc TEXT,completed_at_utc TEXT,builder_version TEXT,input_manifest_sha256 TEXT,database_snapshot_sha256 TEXT,status TEXT);
CREATE TABLE source_files(source_file_id TEXT PRIMARY KEY,dataset_name TEXT,source_path TEXT,source_format TEXT,sha256 TEXT,size_bytes INTEGER,row_count INTEGER,ingest_run_id TEXT);
CREATE TABLE asset_registry(asset_id TEXT PRIMARY KEY,logical_role TEXT,uri TEXT,host TEXT,size_bytes INTEGER,sha256 TEXT,existence_status TEXT,verification_status TEXT,retention_tier TEXT,source_file_id TEXT,evidence_tier TEXT,notes TEXT);
CREATE TABLE data_dictionary(object_name TEXT,column_name TEXT,data_type TEXT,unit TEXT,description TEXT,source_or_formula TEXT,nullable INTEGER,PRIMARY KEY(object_name,column_name));
CREATE TABLE query_catalog(query_id TEXT PRIMARY KEY,title TEXT,query_version TEXT,sql_text TEXT,expected_columns_json TEXT,interpretation_boundary TEXT,sql_sha256 TEXT);
CREATE TABLE tabular_evidence(source_file_id TEXT,row_number INTEGER,table_name TEXT,evidence_tier TEXT,row_json TEXT,PRIMARY KEY(source_file_id,row_number));
CREATE TABLE claims(claim_id TEXT PRIMARY KEY,description TEXT,status TEXT,evidence_path TEXT,interpretation_boundary TEXT);
