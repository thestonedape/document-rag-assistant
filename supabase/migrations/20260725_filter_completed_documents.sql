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
