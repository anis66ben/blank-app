-- Concierge Flow — schéma PostgreSQL / Supabase (MVP)
-- Exécuter dans l'éditeur SQL Supabase. RLS à activer selon les rôles.

create type user_role as enum ('admin', 'manager', 'provider', 'owner');
create type platform as enum ('airbnb', 'booking', 'abritel');
create type task_status as enum (
  'todo', 'proposed', 'accepted', 'in_progress', 'quality_check', 'done', 'incident'
);
create type task_priority as enum ('low', 'medium', 'high');
create type incident_severity as enum ('low', 'medium', 'high');
create type incident_status as enum ('open', 'in_progress', 'resolved');
create type message_direction as enum ('in', 'out');

create table users (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text unique not null,
  role user_role not null default 'manager',
  phone text,
  created_at timestamptz default now()
);

create table properties (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  address text not null,
  capacity int not null default 2,
  cleaning_time int not null default 90,       -- minutes
  quality_check_time int not null default 15,  -- minutes
  door_code text,
  notes text,
  lat double precision,
  lng double precision,
  photo text,
  owner_id uuid references users(id),
  created_at timestamptz default now()
);

create table reservations (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  platform platform not null,
  guest_name text,
  start_date date not null,
  end_date date not null,
  guests_count int default 1
);

create table providers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  phone text,
  zone text,
  rating numeric(2,1) default 0,
  availability_score numeric(3,2) default 0.5
);

create table cleaning_tasks (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  reservation_id uuid references reservations(id) on delete set null,
  provider_id uuid references providers(id) on delete set null,
  date date not null,
  start_time timestamptz,
  end_time timestamptz,
  status task_status not null default 'todo',
  priority task_priority not null default 'medium',
  estimated_time int default 90
);

create table incidents (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  task_id uuid references cleaning_tasks(id) on delete set null,
  type text not null,
  severity incident_severity not null default 'medium',
  description text,
  status incident_status not null default 'open',
  created_at timestamptz default now()
);

create table messages (
  id uuid primary key default gen_random_uuid(),
  provider_id uuid references providers(id) on delete set null,
  property_id uuid references properties(id) on delete set null,
  task_id uuid references cleaning_tasks(id) on delete set null,
  direction message_direction not null,
  content text,
  media_url text,
  created_at timestamptz default now()
);

-- Création automatique de mission à la fin d'une réservation.
create or replace function create_task_on_reservation_end()
returns trigger as $$
begin
  insert into cleaning_tasks (property_id, reservation_id, date, status, priority, estimated_time)
  select new.property_id, new.id, new.end_date, 'todo', 'high',
         coalesce(p.cleaning_time, 90)
  from properties p where p.id = new.property_id;
  return new;
end;
$$ language plpgsql;

create trigger trg_reservation_to_task
after insert on reservations
for each row execute function create_task_on_reservation_end();

-- Temps réel : à activer dans Supabase pour le Gantt / dashboard live.
-- alter publication supabase_realtime add table cleaning_tasks, reservations, incidents;
