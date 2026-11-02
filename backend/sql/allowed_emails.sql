-- Lista de e-mails autorizados a usar o app (checada em verify_user, app/auth.py).
-- Para liberar alguém, basta inserir o e-mail aqui; não precisa mudar código.
-- Rodar uma vez no SQL Editor do Supabase.
create table if not exists allowed_emails (
    email text primary key
);
