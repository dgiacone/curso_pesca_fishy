-- Ejecuta este script en el SQL Editor de Supabase antes de usar el servidor MCP.
-- Estas funciones permiten introspeccionar el schema de la base de datos.

create or replace function get_tables_info()
returns table (
    table_name text,
    table_schema text,
    table_type text,
    row_count bigint
)
language sql
security definer
set search_path = public
as $$
    select
        t.table_name::text,
        t.table_schema::text,
        t.table_type::text,
        coalesce(s.n_live_tup, 0)::bigint as row_count
    from information_schema.tables t
    left join pg_stat_user_tables s
        on s.relname = t.table_name
        and s.schemaname = t.table_schema
    where t.table_schema not in ('pg_catalog', 'information_schema', 'auth', 'storage', 'vault', 'extensions', 'graphql', 'graphql_public', 'realtime', 'pgbouncer', 'pgsodium', 'pgsodium_masks', 'supabase_functions', 'supabase_migrations', '_realtime')
    order by t.table_schema, t.table_name;
$$;

create or replace function get_table_schema(p_table_name text)
returns table (
    column_name text,
    data_type text,
    is_nullable text,
    column_default text,
    character_maximum_length integer
)
language sql
security definer
set search_path = public
as $$
    select
        column_name::text,
        data_type::text,
        is_nullable::text,
        column_default::text,
        character_maximum_length::integer
    from information_schema.columns
    where table_name = p_table_name
      and table_schema not in ('pg_catalog', 'information_schema')
    order by ordinal_position;
$$;

-- Otorga permisos al rol anon y authenticated para llamar a estas funciones
grant execute on function get_tables_info() to anon, authenticated;
grant execute on function get_table_schema(text) to anon, authenticated;
