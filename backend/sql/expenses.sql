-- Gastos capturados automaticamente (ex.: automação "Transação" do Atalhos do iPhone).
-- Rodar uma vez no SQL Editor do Supabase.
create table if not exists expenses (
    id          uuid primary key default gen_random_uuid(),
    amount      numeric(12, 2),            -- nulo quando o banco não informa o valor
    merchant    text,
    card        text,
    occurred_at timestamptz not null,
    source      text not null default 'apple_pay',
    is_test     boolean not null default false,
    raw         jsonb,                     -- payload original, para depurar o parser
    created_at  timestamptz not null default now()
);

create index if not exists expenses_occurred_at_idx on expenses (occurred_at desc) where not is_test;

-- Sem políticas: só o backend (chave secret, que ignora RLS) acessa a tabela.
-- A chave anon, pública no frontend, não lê nem escreve nada.
alter table expenses enable row level security;
