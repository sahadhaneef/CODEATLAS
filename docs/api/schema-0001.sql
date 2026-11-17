BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE repositories (
    id VARCHAR(36) NOT NULL, 
    organization_id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    remote_url VARCHAR(512) NOT NULL, 
    requested_ref VARCHAR(256) NOT NULL, 
    owner_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (organization_id, id)
);

CREATE TABLE index_jobs (
    id VARCHAR(36) NOT NULL, 
    organization_id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    repository_id VARCHAR(36) NOT NULL, 
    requested_by VARCHAR(36) NOT NULL, 
    requested_ref VARCHAR(256) NOT NULL, 
    commit_sha VARCHAR(40), 
    tree_sha VARCHAR(40), 
    status VARCHAR(32) NOT NULL, 
    stage VARCHAR(32) NOT NULL, 
    error_code VARCHAR(64), 
    idempotency_key VARCHAR(128) NOT NULL, 
    request_digest VARCHAR(64) NOT NULL, 
    attempts INTEGER DEFAULT '0' NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (organization_id, id), 
    UNIQUE (organization_id, requested_by, idempotency_key), 
    FOREIGN KEY(organization_id, repository_id) REFERENCES repositories (organization_id, id)
);

CREATE TABLE files (
    id VARCHAR(36) NOT NULL, 
    organization_id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    repository_id VARCHAR(36) NOT NULL, 
    job_id VARCHAR(36) NOT NULL, 
    path VARCHAR(2048) NOT NULL, 
    blob_sha VARCHAR(40) NOT NULL, 
    byte_count INTEGER NOT NULL, 
    inventory_status VARCHAR(32) NOT NULL, 
    exclusion_reason VARCHAR(128), 
    PRIMARY KEY (id), 
    UNIQUE (organization_id, id), 
    UNIQUE (organization_id, job_id, path), 
    FOREIGN KEY(organization_id, repository_id) REFERENCES repositories (organization_id, id), 
    FOREIGN KEY(organization_id, job_id) REFERENCES index_jobs (organization_id, id)
);

CREATE INDEX ix_repositories_organization_id ON repositories (organization_id);

ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;

ALTER TABLE repositories FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_scope ON repositories USING (organization_id = current_setting('app.tenant', true)) WITH CHECK (organization_id = current_setting('app.tenant', true));

CREATE INDEX ix_index_jobs_organization_id ON index_jobs (organization_id);

ALTER TABLE index_jobs ENABLE ROW LEVEL SECURITY;

ALTER TABLE index_jobs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_scope ON index_jobs USING (organization_id = current_setting('app.tenant', true)) WITH CHECK (organization_id = current_setting('app.tenant', true));

CREATE INDEX ix_files_organization_id ON files (organization_id);

ALTER TABLE files ENABLE ROW LEVEL SECURITY;

ALTER TABLE files FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_scope ON files USING (organization_id = current_setting('app.tenant', true)) WITH CHECK (organization_id = current_setting('app.tenant', true));

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

COMMIT;

