-- Run this script in the SQL Editor of a Supabase project you own.
-- The api_private schema is not exposed through the Supabase Data API.

create schema if not exists api_private;
revoke all on schema api_private from public, anon, authenticated;

create table if not exists api_private.api_clients (
    id text primary key,
    name text not null check (length(name) between 1 and 200),
    key_prefix text not null,
    key_hash text not null unique check (key_hash ~ '^[0-9a-f]{64}$'),
    active boolean not null default true,
    requests_per_minute integer not null default 10
        check (requests_per_minute between 1 and 10000),
    created_at timestamptz not null default now(),
    revoked_at timestamptz,
    constraint api_clients_revocation_consistent check (
        (active and revoked_at is null) or (not active and revoked_at is not null)
    )
);

create table if not exists api_private.api_rate_windows (
    client_id text not null references api_private.api_clients(id) on delete cascade,
    window_start timestamptz not null,
    request_count integer not null default 1 check (request_count > 0),
    updated_at timestamptz not null default now(),
    primary key (client_id, window_start)
);

create index if not exists api_rate_windows_expiry_idx
    on api_private.api_rate_windows (window_start);

create table if not exists api_private.api_usage (
    id bigint generated always as identity primary key,
    client_id text not null references api_private.api_clients(id) on delete restrict,
    request_id text not null unique,
    question_hash text not null check (question_hash ~ '^[0-9a-f]{64}$'),
    status_code smallint not null check (status_code between 100 and 599),
    row_count integer not null default 0 check (row_count >= 0),
    duration_ms numeric(12, 2) not null check (duration_ms >= 0),
    created_at timestamptz not null default now()
);

create index if not exists api_usage_client_created_idx
    on api_private.api_usage (client_id, created_at desc);

alter table api_private.api_clients enable row level security;
alter table api_private.api_rate_windows enable row level security;
alter table api_private.api_usage enable row level security;

revoke all on all tables in schema api_private from public, anon, authenticated;
revoke all on all sequences in schema api_private from public, anon, authenticated;

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'api_query_engine') then
        create role api_query_engine nologin;
    end if;
end
$$;

grant usage on schema api_private to api_query_engine;
grant select, insert, update on api_private.api_clients to api_query_engine;
grant select, insert, update on api_private.api_rate_windows to api_query_engine;
grant insert on api_private.api_usage to api_query_engine;
grant select (request_id) on api_private.api_usage to api_query_engine;
grant usage, select on sequence api_private.api_usage_id_seq to api_query_engine;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'api_private'
          and tablename = 'api_clients'
          and policyname = 'api_clients_backend_access'
    ) then
        create policy api_clients_backend_access on api_private.api_clients
            for all to api_query_engine using (true) with check (true);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'api_private'
          and tablename = 'api_rate_windows'
          and policyname = 'api_rate_windows_backend_access'
    ) then
        create policy api_rate_windows_backend_access on api_private.api_rate_windows
            for all to api_query_engine using (true) with check (true);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'api_private'
          and tablename = 'api_usage'
          and policyname = 'api_usage_backend_insert'
    ) then
        create policy api_usage_backend_insert on api_private.api_usage
            for insert to api_query_engine with check (true);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'api_private'
          and tablename = 'api_usage'
          and policyname = 'api_usage_backend_conflict_check'
    ) then
        create policy api_usage_backend_conflict_check on api_private.api_usage
            for select to api_query_engine using (true);
    end if;
end
$$;

comment on schema api_private is
    'Private backend-only API clients, fixed-window counters, and usage audit data.';
comment on column api_private.api_clients.key_hash is
    'SHA-256 digest of a high-entropy partner API key; plaintext is never stored.';
comment on column api_private.api_usage.question_hash is
    'SHA-256 digest for correlation without retaining natural-language question content.';

-- Optional scheduled cleanup, or run it from an external cron job:
-- delete from api_private.api_rate_windows where window_start < now() - interval '1 day';

-- Create a separate login role with a strong generated password, then grant it only this role:
-- create role api_query_engine_login login password 'GENERATE_A_LONG_RANDOM_PASSWORD';
-- grant api_query_engine to api_query_engine_login;
