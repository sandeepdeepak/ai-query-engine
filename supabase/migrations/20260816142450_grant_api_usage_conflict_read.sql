-- INSERT ... ON CONFLICT (request_id) requires SELECT on the conflict target.
-- Keep the backend role restricted to that single column rather than granting
-- read access to complete usage records.
grant select (request_id) on api_private.api_usage to api_query_engine;
