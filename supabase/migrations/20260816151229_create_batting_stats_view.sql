create or replace view public.batting_stats
with (security_invoker = true)
as
select
    m.season_year,
    i.batting_team_id,
    i.batting_team_name,
    d.batter_id,
    d.batter_name,
    sum(d.batting_runs)::bigint as runs,
    count(distinct d.match_id)::bigint as matches,
    count(*) filter (where d.batting_runs = 4)::bigint as fours,
    count(*) filter (where d.batting_runs = 6)::bigint as sixes
from public.deliveries as d
join public.innings as i
  on i.match_id = d.match_id
 and i.innings_number = d.innings_number
join public.matches as m
  on m.match_id = d.match_id
group by
    m.season_year,
    i.batting_team_id,
    i.batting_team_name,
    d.batter_id,
    d.batter_name;

comment on view public.batting_stats is
    'Player-level IPL batting totals grouped by season and the team represented.';

grant select on public.batting_stats to anon, authenticated;
