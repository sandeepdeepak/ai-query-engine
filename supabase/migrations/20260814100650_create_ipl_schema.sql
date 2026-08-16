
CREATE TABLE public.seasons (season_year integer PRIMARY KEY, competition_id text NOT NULL UNIQUE, season_id text, competition_name text, feedsource text NOT NULL);
CREATE TABLE public.matches (match_id text PRIMARY KEY, season_year integer NOT NULL REFERENCES public.seasons(season_year), data_source text NOT NULL DEFAULT 'cricsheet', source_url text, match_number text, match_date date, start_time text, status text, home_team_id text, home_team_name text, away_team_id text, away_team_name text, venue text, city text, result_text text, winner_team_id text, toss_winner text, toss_decision text, target text, current_innings text, details_loaded boolean NOT NULL DEFAULT false, updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE public.players (player_id text PRIMARY KEY, player_name text NOT NULL, player_short_name text, image_url text, first_seen_season integer NOT NULL, last_seen_season integer NOT NULL);
CREATE TABLE public.player_seasons (player_id text NOT NULL REFERENCES public.players(player_id), season_year integer NOT NULL REFERENCES public.seasons(season_year), team_id text NOT NULL DEFAULT '', team_name text, PRIMARY KEY (player_id, season_year, team_id));
CREATE TABLE public.innings (match_id text NOT NULL REFERENCES public.matches(match_id) ON DELETE CASCADE, innings_number integer NOT NULL, batting_team_id text, batting_team_name text, bowling_team_id text, bowling_team_name text, runs integer, wickets integer, overs text, extras integer, status text, PRIMARY KEY (match_id, innings_number));
CREATE TABLE public.batting_cards (match_id text NOT NULL, innings_number integer NOT NULL, position integer NOT NULL, player_id text REFERENCES public.players(player_id), player_name text, team_id text, dismissal text, runs integer, balls integer, fours integer, sixes integer, strike_rate double precision, is_not_out boolean, PRIMARY KEY (match_id, innings_number, position), FOREIGN KEY (match_id, innings_number) REFERENCES public.innings(match_id, innings_number) ON DELETE CASCADE);
CREATE TABLE public.bowling_cards (match_id text NOT NULL, innings_number integer NOT NULL, position integer NOT NULL, player_id text REFERENCES public.players(player_id), player_name text, team_id text, overs text, maidens integer, runs_conceded integer, wickets integer, economy double precision, dots integer, fours integer, sixes integer, wides integer, no_balls integer, PRIMARY KEY (match_id, innings_number, position), FOREIGN KEY (match_id, innings_number) REFERENCES public.innings(match_id, innings_number) ON DELETE CASCADE);
CREATE TABLE public.fall_of_wickets (match_id text NOT NULL, innings_number integer NOT NULL, wicket_number integer NOT NULL, player_id text REFERENCES public.players(player_id), player_name text, score text, over text, PRIMARY KEY (match_id, innings_number, wicket_number), FOREIGN KEY (match_id, innings_number) REFERENCES public.innings(match_id, innings_number) ON DELETE CASCADE);
CREATE TABLE public.deliveries (match_id text NOT NULL, innings_number integer NOT NULL, sequence integer NOT NULL, over_number integer, ball_number integer, ball_label text, batter_id text, batter_name text, non_striker_id text, non_striker_name text, bowler_id text, bowler_name text, batting_runs integer, extra_runs integer, total_runs integer, extras_type text, is_wicket boolean, dismissed_player_id text, dismissed_player_name text, dismissal_kind text, fielder_name text, score text, commentary text, PRIMARY KEY (match_id, innings_number, sequence), FOREIGN KEY (match_id, innings_number) REFERENCES public.innings(match_id, innings_number) ON DELETE CASCADE);
CREATE INDEX idx_matches_season ON public.matches(season_year);
CREATE INDEX idx_player_seasons_season ON public.player_seasons(season_year, team_id);
CREATE INDEX idx_batting_player ON public.batting_cards(player_id);
CREATE INDEX idx_bowling_player ON public.bowling_cards(player_id);
CREATE INDEX idx_deliveries_match ON public.deliveries(match_id, innings_number, over_number);
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['seasons','matches','players','player_seasons','innings','batting_cards','bowling_cards','fall_of_wickets','deliveries']
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('GRANT SELECT ON public.%I TO authenticated', t);
    EXECUTE format('GRANT INSERT ON public.%I TO anon', t);
    EXECUTE format('CREATE POLICY authenticated_read ON public.%I FOR SELECT TO authenticated USING (true)', t);
    EXECUTE format('CREATE POLICY temporary_import ON public.%I FOR INSERT TO anon WITH CHECK ((current_setting(''request.headers'', true)::jsonb ->> ''x-import-token'') = %L)', t, 'msss8l0j-zwz0rcjsq5d-hvt05vj9w0r');
  END LOOP;
END $$;
;
