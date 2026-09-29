create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    original_filename text not null,
    storage_path text not null unique,
    file_size bigint,
    page_count integer,
    status text not null default 'processing'
        check (status in ('processing', 'completed', 'failed')),
    error_message text,
    created_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references public.documents(id) on delete cascade,
    chunk_index integer not null,
    page_number integer not null,
    text text not null,
    token_count integer,
    embedding vector(384) not null,
    created_at timestamptz not null default now(),
    unique (document_id, chunk_index)
);

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    title text,
    created_at timestamptz not null default now()
);

create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    citations jsonb not null default '[]'::jsonb,
    latency_ms integer,
    created_at timestamptz not null default now()
);

create table if not exists public.feedback (
    id uuid primary key default gen_random_uuid(),
    message_id uuid not null references public.messages(id) on delete cascade,
    rating text not null check (rating in ('positive', 'negative')),
    comment text,
    created_at timestamptz not null default now()
);

create index if not exists document_chunks_document_id_idx
    on public.document_chunks(document_id);

create index if not exists document_chunks_embedding_idx
    on public.document_chunks
    using hnsw (embedding vector_cosine_ops);

create index if not exists messages_conversation_id_created_at_idx
    on public.messages(conversation_id, created_at);

create or replace function public.match_document_chunks(
    query_embedding vector(384),
    match_count integer default 5,
    filter_document_ids uuid[] default null
)
returns table (
    id uuid,
    document_id uuid,
    chunk_index integer,
    page_number integer,
    text text,
    similarity float
)
language sql
stable
as $$
    select
        dc.id,
        dc.document_id,
        dc.chunk_index,
        dc.page_number,
        dc.text,
        1 - (dc.embedding <=> query_embedding) as similarity
    from public.document_chunks dc
    join public.documents d on d.id = dc.document_id
    where
        d.status = 'completed'
        and (
            filter_document_ids is null
            or dc.document_id = any(filter_document_ids)
        )
    order by dc.embedding <=> query_embedding
    limit greatest(match_count, 1);
$$;

alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.feedback enable row level security;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'documents',
    'documents',
    false,
    26214400,
    array['application/pdf']
)
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- The backend uses the Supabase service-role key, which bypasses RLS.
-- Do not add anonymous write policies or expose the service-role key to React.
