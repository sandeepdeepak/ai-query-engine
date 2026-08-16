create or replace view public.player_match_batting
with (security_invoker = true)
as
select
    m.season_year,
    m.match_id,
    m.match_date,
    i.innings_number,
    i.batting_team_id,
    i.batting_team_name,
    i.bowling_team_id as opponent_team_id,
    i.bowling_team_name as opponent_team_name,
    d.batter_id,
    d.batter_name,
    sum(d.batting_runs)::bigint as runs,
    count(*) filter (where coalesce(d.extras_type, '') not like '%wides%')::bigint
        as balls_faced,
    count(*) filter (where d.batting_runs = 4)::bigint as fours,
    count(*) filter (where d.batting_runs = 6)::bigint as sixes,
    round(
        sum(d.batting_runs)::numeric * 100
        / nullif(count(*) filter (where coalesce(d.extras_type, '') not like '%wides%'), 0),
        2
    ) as strike_rate
from public.deliveries as d
join public.innings as i
  on i.match_id = d.match_id
 and i.innings_number = d.innings_number
join public.matches as m on m.match_id = d.match_id
group by
    m.season_year, m.match_id, m.match_date, i.innings_number,
    i.batting_team_id, i.batting_team_name, i.bowling_team_id,
    i.bowling_team_name, d.batter_id, d.batter_name;

create or replace view public.player_match_bowling
with (security_invoker = true)
as
select
    m.season_year,
    m.match_id,
    m.match_date,
    i.innings_number,
    i.bowling_team_id,
    i.bowling_team_name,
    i.batting_team_id as opponent_team_id,
    i.batting_team_name as opponent_team_name,
    d.bowler_id,
    d.bowler_name,
    count(*) filter (
        where coalesce(d.extras_type, '') not like '%wides%'
          and coalesce(d.extras_type, '') not like '%noballs%'
    )::bigint as legal_balls,
    sum(
        d.total_runs - case
            when coalesce(d.extras_type, '') ~ '(^|,)(byes|legbyes|penalty)(,|$)'
                then d.extra_runs
            else 0
        end
    )::bigint as runs_conceded,
    count(*) filter (
        where d.is_wicket
          and d.dismissal_kind not in (
              'run out', 'retired hurt', 'retired out', 'obstructing the field'
          )
    )::bigint as wickets,
    round(
        sum(
            d.total_runs - case
                when coalesce(d.extras_type, '') ~ '(^|,)(byes|legbyes|penalty)(,|$)'
                    then d.extra_runs
                else 0
            end
        )::numeric * 6
        / nullif(count(*) filter (
            where coalesce(d.extras_type, '') not like '%wides%'
              and coalesce(d.extras_type, '') not like '%noballs%'
        ), 0),
        2
    ) as economy
from public.deliveries as d
join public.innings as i
  on i.match_id = d.match_id
 and i.innings_number = d.innings_number
join public.matches as m on m.match_id = d.match_id
group by
    m.season_year, m.match_id, m.match_date, i.innings_number,
    i.bowling_team_id, i.bowling_team_name, i.batting_team_id,
    i.batting_team_name, d.bowler_id, d.bowler_name;

create or replace view public.bowling_stats
with (security_invoker = true)
as
select
    season_year,
    bowling_team_id,
    bowling_team_name,
    bowler_id,
    bowler_name,
    count(distinct match_id)::bigint as matches,
    sum(legal_balls)::bigint as legal_balls,
    sum(runs_conceded)::bigint as runs_conceded,
    sum(wickets)::bigint as wickets,
    round(sum(runs_conceded)::numeric * 6 / nullif(sum(legal_balls), 0), 2) as economy
from public.player_match_bowling
group by season_year, bowling_team_id, bowling_team_name, bowler_id, bowler_name;

create or replace view public.team_season_stats
with (security_invoker = true)
as
with team_matches as (
    select
        season_year, match_id, status, result_text, winner_team_id,
        home_team_id as team_id, home_team_name as team_name
    from public.matches
    union all
    select
        season_year, match_id, status, result_text, winner_team_id,
        away_team_id as team_id, away_team_name as team_name
    from public.matches
)
select
    season_year,
    team_id,
    team_name,
    count(*) filter (where status = 'completed')::bigint as matches_played,
    count(*) filter (
        where status = 'completed'
          and winner_team_id in (team_id, team_name)
    )::bigint as wins,
    count(*) filter (
        where status = 'completed'
          and winner_team_id is not null
          and winner_team_id not in (team_id, team_name)
          and coalesce(result_text, '') not ilike '%tied%'
    )::bigint as losses,
    count(*) filter (
        where status = 'completed'
          and (winner_team_id is null or coalesce(result_text, '') ilike '%no result%')
    )::bigint as no_results,
    count(*) filter (
        where status = 'completed' and coalesce(result_text, '') ilike '%tied%'
    )::bigint as ties,
    round(
        count(*) filter (
            where status = 'completed' and winner_team_id in (team_id, team_name)
        )::numeric * 100
        / nullif(count(*) filter (where status = 'completed'), 0),
        2
    ) as win_percentage
from team_matches
group by season_year, team_id, team_name;

create or replace view public.head_to_head_stats
with (security_invoker = true)
as
select
    season_year,
    least(home_team_name, away_team_name) as team1_name,
    greatest(home_team_name, away_team_name) as team2_name,
    count(*) filter (where status = 'completed')::bigint as matches_played,
    count(*) filter (
        where status = 'completed'
          and winner_team_id = least(home_team_name, away_team_name)
    )::bigint as team1_wins,
    count(*) filter (
        where status = 'completed'
          and winner_team_id = greatest(home_team_name, away_team_name)
    )::bigint as team2_wins,
    count(*) filter (
        where status = 'completed'
          and (winner_team_id is null or coalesce(result_text, '') ilike '%no result%')
    )::bigint as no_results,
    count(*) filter (
        where status = 'completed' and coalesce(result_text, '') ilike '%tied%'
    )::bigint as ties
from public.matches
group by season_year, least(home_team_name, away_team_name), greatest(home_team_name, away_team_name);

create or replace view public.venue_stats
with (security_invoker = true)
as
select
    m.season_year,
    m.venue,
    m.city,
    count(*) filter (where m.status = 'completed')::bigint as matches_played,
    round(avg(i1.runs) filter (where m.status = 'completed'), 2) as average_first_innings_runs,
    max(i1.runs) filter (where m.status = 'completed') as highest_first_innings_runs,
    count(*) filter (
        where m.status = 'completed'
          and m.winner_team_id in (i1.batting_team_id, i1.batting_team_name)
    )::bigint as batting_first_wins,
    count(*) filter (
        where m.status = 'completed'
          and m.winner_team_id in (i2.batting_team_id, i2.batting_team_name)
    )::bigint as chasing_wins,
    count(*) filter (
        where m.status = 'completed'
          and (m.winner_team_id is null or coalesce(m.result_text, '') ilike '%no result%')
    )::bigint as no_results
from public.matches as m
left join public.innings as i1
  on i1.match_id = m.match_id and i1.innings_number = 1
left join public.innings as i2
  on i2.match_id = m.match_id and i2.innings_number = 2
group by m.season_year, m.venue, m.city;

comment on view public.bowling_stats is
    'Season/team/bowler IPL bowling totals with bowler-attributed wickets and economy.';
comment on view public.player_match_batting is
    'Per-match IPL batting scorecard totals for each batter.';
comment on view public.player_match_bowling is
    'Per-match IPL bowling figures for each bowler.';
comment on view public.team_season_stats is
    'IPL team results and win percentage by season.';
comment on view public.head_to_head_stats is
    'IPL results for a canonical pair of teams by season.';
comment on view public.venue_stats is
    'IPL venue scoring and result patterns by season.';

grant select on public.bowling_stats to anon, authenticated;
grant select on public.player_match_batting to anon, authenticated;
grant select on public.player_match_bowling to anon, authenticated;
grant select on public.team_season_stats to anon, authenticated;
grant select on public.head_to_head_stats to anon, authenticated;
grant select on public.venue_stats to anon, authenticated;
