-- ============================================================================
-- CREATE TABLES
-- ============================================================================
-- Main database tables in correct dependency order
-- ============================================================================

-- Set search path for the session
SET search_path = public; -- app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Creating tables... and instagram_accounts';
    RAISE NOTICE '==============================================';
END $$;

-- Create updated_at trigger function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create Table
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL, --REFERENCES owners(owner_id) ON DELETE CASCADE,
    phone_number TEXT,
    access_token TEXT NOT NULL,
    api_id TEXT NOT NULL,
    app_secret TEXT NOT NULL,
    verify_token TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_instagram_accounts_owner_id UNIQUE (owner_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_owner_id ON instagram_accounts(owner_id);

COMMENT ON INDEX idx_instagram_accounts_owner_id IS 'Index on owner_id for faster queries';

-- Triggers
DROP TRIGGER IF EXISTS update_instagram_accounts_updated_at ON instagram_accounts;
CREATE TRIGGER update_instagram_accounts_updated_at
BEFORE UPDATE ON instagram_accounts
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Creating table: instagram_accounts';
    RAISE NOTICE '==============================================';
END $$;
