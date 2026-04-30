-- Ba Me Oi AI family memory schema.
-- Run this once in Supabase SQL Editor before public launch.

create table if not exists family_profiles (
  user_id text primary key,
  family_id text not null,
  role text not null default 'con',
  display_name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists family_documents (
  id text primary key,
  family_id text not null,
  user_id text not null,
  title text not null,
  doc_type text not null default 'general',
  doc_label text not null default 'Giấy tờ gia đình',
  overview text not null default '',
  structured_summary jsonb not null default '{}'::jsonb,
  family_intelligence jsonb not null default '{}'::jsonb,
  source text not null default 'zalo',
  created_at timestamptz not null default now()
);

create table if not exists family_deadlines (
  id text primary key,
  user_id text not null,
  task text not null,
  date text not null,
  assignee text not null default '',
  note text not null default '',
  doc_title text not null default '',
  doc_type text not null default 'general',
  created_at text not null default '',
  status text not null default 'active'
);

create index if not exists idx_family_documents_user_created
  on family_documents (user_id, created_at desc);

create index if not exists idx_family_documents_family_created
  on family_documents (family_id, created_at desc);

create index if not exists idx_family_deadlines_user_date
  on family_deadlines (user_id, date);

create index if not exists idx_family_deadlines_status
  on family_deadlines (status);
