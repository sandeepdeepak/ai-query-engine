-- ON CONFLICT reads the candidate conflict row. Combined with the existing
-- column-level grant, this policy exposes only request_id to the backend role.
create policy api_usage_backend_conflict_check on api_private.api_usage
    for select to api_query_engine using (true);
