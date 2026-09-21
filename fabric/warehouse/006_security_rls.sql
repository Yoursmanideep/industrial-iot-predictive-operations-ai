CREATE SCHEMA security;

CREATE TABLE security.user_plant_access (
    access_sk BIGINT IDENTITY,
    user_principal_name VARCHAR(320) NOT NULL,
    plant_id VARCHAR(20) NOT NULL,
    access_role VARCHAR(50) NOT NULL,
    is_active BIT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    created_at_utc DATETIME2(3) NOT NULL,
    updated_at_utc DATETIME2(3) NOT NULL
);

-- Deployment seeds are intentionally placeholders.
-- Replace user principals through the environment-specific security pipeline.
INSERT INTO security.user_plant_access (
    user_principal_name, plant_id, access_role, is_active,
    effective_from, effective_to, created_at_utc, updated_at_utc
)
VALUES
    ('enterprise.viewer@apexindustrial.example', 'PLT-CHN-01', 'ENTERPRISE_VIEWER', 1, CAST('2026-01-01' AS DATE), NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('enterprise.viewer@apexindustrial.example', 'PLT-PUN-01', 'ENTERPRISE_VIEWER', 1, CAST('2026-01-01' AS DATE), NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('enterprise.viewer@apexindustrial.example', 'PLT-CBE-01', 'ENTERPRISE_VIEWER', 1, CAST('2026-01-01' AS DATE), NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Additional plant-specific principals are provisioned outside source control.
-- Semantic-model RLS filters the Plant dimension by USERPRINCIPALNAME().