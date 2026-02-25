-- ============================================================================
-- DROP DATABASE - Remove all objects in correct dependency order
-- ============================================================================
-- WARNING: This script will permanently delete all data and objects!
-- Execute with caution.
-- ============================================================================

-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Starting database cleanup...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- 1. DROP VIEWS
-- ============================================================================


-- ============================================================================
-- 2. DROP TABLES (in reverse dependency order)
-- ============================================================================
-- Drop table
DROP TABLE IF EXISTS public.instagram_accounts CASCADE;


-- Drop child tables first (tables with foreign keys)

-- ============================================================================
-- 3. DROP FUNCTIONS and TRIGGERS
-- ============================================================================
DO $$
BEGIN
    IF to_regclass('public.instagram_accounts') IS NOT NULL THEN
        EXECUTE 'DROP TRIGGER IF EXISTS update_instagram_accounts_updated_at ON instagram_accounts';
    END IF;
END $$;

DROP FUNCTION IF EXISTS public.update_updated_at_column();

-- ============================================================================
-- 4. DROP INDEXES (if any standalone indexes remain)
-- ============================================================================
-- Most indexes are dropped with their tables via CASCADE
-- This section is for any orphaned indexes
DROP INDEX IF EXISTS public.idx_instagram_accounts_owner_id;
DROP INDEX IF EXISTS public.idx_instagram_accounts_business_id;

-- ============================================================================
-- 5. DROP TYPES (if any custom types exist)
-- ============================================================================
-- Add custom types here if needed

-- ============================================================================
-- 6. DROP EXTENSIONS (optional - be careful with shared extensions)
-- ============================================================================
-- Uncomment if you want to remove extensions

-- ============================================================================
-- 7. DROP SCHEMAS (optional - only if you created custom schemas)
-- ============================================================================
-- DROP SCHEMA IF EXISTS app CASCADE;



-- Re-enable foreign key checks
SET session_replication_role = 'origin';

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Database cleanup completed!';
    RAISE NOTICE 'All tables, functions, and views removed.';
    RAISE NOTICE '==============================================';
END $$;
