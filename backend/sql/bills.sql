-- Contas recorrentes. O status de pagamento não fica aqui: é derivado dos
-- comprovantes na pasta do Google Drive de cada conta (drive_folder_id).
-- Rodar uma vez no SQL Editor do Supabase.
create table if not exists bills (
    id              uuid primary key default gen_random_uuid(),
    name            text not null,
    due_day         integer not null,  -- dia do vencimento; acima do fim do mês é ajustado para o último dia
    drive_folder_id text not null,
    start_date      date               -- primeiro mês cobrado; nulo = cobrada desde janeiro
);

-- Sem políticas: só o backend (chave secret, que ignora RLS) acessa a tabela.
alter table bills enable row level security;
